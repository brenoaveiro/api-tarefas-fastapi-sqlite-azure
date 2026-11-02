"""
CyberIncident API - Plataforma de Gerenciamento de Incidentes de Seguranca Cibernetica.

Aplicacao academica que simula o registro de incidentes de um SOC (Security
Operations Center). Todos os dados sao ficticios. Define os endpoints HTTP,
o dashboard (GET /), o Swagger personalizado (GET /docs) e o tratamento de erros.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import crud
from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.enums import Categoria, Severidade, StatusIncidente
from app.schemas import (ErroOut, EstatisticasOut, HealthOut, IncidenteCreate, IncidenteListOut,
                         IncidenteOut, IncidenteUpdate, StatusUpdate)

logger = logging.getLogger("cyberincident")
logging.basicConfig(level=logging.INFO)

STATIC_DIR = Path(__file__).resolve().parent / "static"
SUBTITULO = "Plataforma de Gerenciamento de Incidentes de Seguranca Cibernetica"

DESCRICAO = f"""
**{SUBTITULO}**

API REST academica que simula uma central de operacoes de seguranca (SOC): permite
**registrar, consultar, classificar, acompanhar e gerenciar incidentes** de seguranca.

* Persistencia em **SQLite** (tabela `incidentes`), hospedada em uma VM **Microsoft Azure**.
* Severidade: `baixa`, `media`, `alta`, `critica`. Status: `aberto`, `em_analise`, `contido`, `resolvido`.
* Operacoes de **escrita** (POST, PUT, PATCH, DELETE) sao restritas por IP no Nginx; leituras (GET) sao publicas.
* **Todos os dados sao ficticios.** IPs de exemplo usam faixas reservadas para documentacao (RFC 5737).
* A conexao e **HTTP** (sem HTTPS): nao ha dominio proprio para emitir certificado.
"""

TAGS = [
    {"name": "Sistema", "description": "Disponibilidade da API e conexao com o SQLite."},
    {"name": "Incidentes", "description": "Cadastro, consulta, atualizacao e exclusao de incidentes de seguranca."},
    {"name": "Estatisticas", "description": "Indicadores calculados a partir dos registros reais do SQLite."},
]


def _criar_dados_demo_se_vazio() -> None:
    """Insere incidentes FICTICIOS de exemplo, apenas se SEED_DEMO_DATA estiver ativo e o banco vazio."""
    if not settings.SEED_DEMO_DATA:
        return
    db = SessionLocal()
    try:
        if crud.listar(db, 0, 1)[0] == 0:
            for t, c, s, ip, a in [
                ("[DEMO] Tentativas de login em excesso", "forca_bruta", "alta", "203.0.113.10", "srv-web-01"),
                ("[DEMO] E-mail suspeito de phishing", "phishing", "media", None, "caixa-financeiro"),
            ]:
                crud.criar(db, IncidenteCreate(titulo=t, descricao="Registro ficticio para demonstracao academica.",
                                               categoria=c, severidade=s, ip_origem=ip, ativo_afetado=a))
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Migracao nao destrutiva e repetivel: cria apenas as tabelas ausentes (ex.: `incidentes`).
    # A tabela antiga `tarefas`, se existir no arquivo, nao e tocada.
    Base.metadata.create_all(bind=engine)
    _criar_dados_demo_se_vazio()
    logger.info("Aplicacao iniciada. Banco de dados: %s", settings.DATABASE_URL)
    yield
    logger.info("Aplicacao finalizada.")


app = FastAPI(
    title=settings.APP_NAME,
    summary=SUBTITULO,
    description=DESCRICAO,
    version=settings.APP_VERSION,
    openapi_tags=TAGS,
    docs_url=None,       # /docs e servido por rota propria (assets locais + tema)
    redoc_url=None,      # evita dependencia de CDN externo
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.exception_handler(SQLAlchemyError)
async def erro_banco_handler(request, exc: SQLAlchemyError):
    logger.exception("Erro de banco de dados")
    return JSONResponse(status_code=500, content={"detail": "Erro interno ao acessar o banco de dados."})


@app.exception_handler(Exception)
async def erro_generico_handler(request, exc: Exception):
    logger.exception("Erro inesperado")
    return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor."})


# ----------------------------------------------------------------- interface

@app.get("/", include_in_schema=False)
def dashboard():
    resposta = FileResponse(STATIC_DIR / "index.html", media_type="text/html; charset=utf-8")
    resposta.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
        "object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    return resposta


@app.get("/docs", include_in_schema=False)
def swagger_personalizado():
    pagina = get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{settings.APP_NAME} - Swagger",
        swagger_js_url="/static/swagger/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger/swagger-ui.css",
        swagger_favicon_url="/static/favicon.svg",
        swagger_ui_parameters={"docExpansion": "list", "defaultModelsExpandDepth": -1, "displayRequestDuration": True,
                               "tagsSorter": "alpha", "persistAuthorization": False},
    )
    html = pagina.body.decode("utf-8").replace(
        "</head>", '<link rel="stylesheet" type="text/css" href="/static/swagger-tema.css">'
                   '<script src="/static/swagger-tema.js" defer></script></head>', 1)
    return HTMLResponse(html)


# ------------------------------------------------------------------- sistema

@app.get("/health", response_model=HealthOut, tags=["Sistema"], summary="Verifica a saude da API e do banco")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        banco = "ok"
    except SQLAlchemyError:
        logger.exception("Falha no health check do banco")
        banco = "erro"
    return JSONResponse(status_code=200 if banco == "ok" else 503,
                        content={"status": "ok" if banco == "ok" else "degradado",
                                 "database": banco, "version": settings.APP_VERSION})


# ---------------------------------------------------------------- incidentes

@app.get("/incidentes", response_model=IncidenteListOut, tags=["Incidentes"],
         summary="Lista incidentes (paginado, com filtros)")
def listar_incidentes(
    skip: int = Query(0, ge=0, description="Registros a ignorar (paginacao)."),
    limit: int = Query(20, ge=1, le=settings.MAX_PAGE_SIZE, description="Maximo de registros retornados."),
    severidade: Optional[Severidade] = Query(None, description="Filtra por severidade."),
    status_: Optional[StatusIncidente] = Query(None, alias="status", description="Filtra por status."),
    categoria: Optional[Categoria] = Query(None, description="Filtra por categoria."),
    db: Session = Depends(get_db),
):
    total, itens = crud.listar(db, skip, limit, severidade.value if severidade else None,
                               status_.value if status_ else None, categoria.value if categoria else None)
    return {"total": total, "skip": skip, "limit": limit, "items": itens}


# IMPORTANTE: /estatisticas deve vir ANTES de /{incidente_id} para nao ser tratada como um ID.
@app.get("/incidentes/estatisticas", response_model=EstatisticasOut, tags=["Estatisticas"],
         summary="Estatisticas dos incidentes (calculadas no SQLite)")
def estatisticas(db: Session = Depends(get_db)):
    return crud.estatisticas(db)


@app.get("/incidentes/{incidente_id}", response_model=IncidenteOut, tags=["Incidentes"],
         summary="Consulta um incidente", responses={404: {"model": ErroOut, "description": "Incidente nao encontrado"}})
def obter_incidente(incidente_id: int, db: Session = Depends(get_db)):
    inc = crud.obter(db, incidente_id)
    if inc is None:
        raise HTTPException(status_code=404, detail="Incidente nao encontrado.")
    return inc


@app.post("/incidentes", response_model=IncidenteOut, status_code=status.HTTP_201_CREATED, tags=["Incidentes"],
          summary="Registra um novo incidente (status inicial: aberto)")
def criar_incidente(dados: IncidenteCreate, db: Session = Depends(get_db)):
    return crud.criar(db, dados)


@app.put("/incidentes/{incidente_id}", response_model=IncidenteOut, tags=["Incidentes"],
         summary="Atualiza um incidente (todos os campos)",
         responses={404: {"model": ErroOut, "description": "Incidente nao encontrado"}})
def atualizar_incidente(incidente_id: int, dados: IncidenteUpdate, db: Session = Depends(get_db)):
    inc = crud.obter(db, incidente_id)
    if inc is None:
        raise HTTPException(status_code=404, detail="Incidente nao encontrado.")
    try:
        return crud.atualizar(db, inc, dados)
    except crud.TransicaoInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.patch("/incidentes/{incidente_id}/status", response_model=IncidenteOut, tags=["Incidentes"],
           summary="Altera somente o status (respeita o fluxo de tratamento)",
           responses={404: {"model": ErroOut, "description": "Incidente nao encontrado"}})
def alterar_status(incidente_id: int, dados: StatusUpdate, db: Session = Depends(get_db)):
    inc = crud.obter(db, incidente_id)
    if inc is None:
        raise HTTPException(status_code=404, detail="Incidente nao encontrado.")
    try:
        return crud.alterar_status(db, inc, dados.status)
    except crud.TransicaoInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.delete("/incidentes/{incidente_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Incidentes"],
            summary="Exclui um incidente (de demonstracao)",
            responses={404: {"model": ErroOut, "description": "Incidente nao encontrado"}})
def excluir_incidente(incidente_id: int, db: Session = Depends(get_db)):
    inc = crud.obter(db, incidente_id)
    if inc is None:
        raise HTTPException(status_code=404, detail="Incidente nao encontrado.")
    crud.excluir(db, inc)
