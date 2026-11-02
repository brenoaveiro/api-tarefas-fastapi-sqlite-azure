"""
Ponto de entrada da API de Gerenciamento de Tarefas.

Define os endpoints HTTP, o ciclo de vida da aplicacao (criacao das
tabelas na inicializacao) e o tratamento de erros.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import crud
from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.schemas import ErroOut, HealthOut, TarefaCreate, TarefaListOut, TarefaOut, TarefaUpdate

logger = logging.getLogger("api_tarefas")
logging.basicConfig(level=logging.INFO)


def _criar_dados_demo_se_vazio() -> None:
    """Popula o banco com tarefas de exemplo, somente se estiver vazio e
    SEED_DEMO_DATA estiver habilitado. Util para demonstracoes locais."""
    if not settings.SEED_DEMO_DATA:
        return
    db = SessionLocal()
    try:
        if crud.contar_tarefas(db) == 0:
            exemplos = [
                TarefaCreate(titulo="Estudar para a prova de Redes", descricao="Revisar capitulo 4."),
                TarefaCreate(titulo="Configurar a VM na Azure", descricao="Criar Resource Group e VM Standard_B1s."),
                TarefaCreate(titulo="Escrever o relatorio tecnico", descricao=None, concluida=True),
            ]
            for exemplo in exemplos:
                crud.criar_tarefa(db, exemplo)
            logger.info("Dados de demonstracao inseridos (SEED_DEMO_DATA=true).")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cria as tabelas automaticamente caso ainda nao existam. Em um banco
    # ja existente (ex.: apos reiniciar a VM), esta chamada e segura e
    # nao apaga dados.
    Base.metadata.create_all(bind=engine)
    _criar_dados_demo_se_vazio()
    logger.info("Aplicacao iniciada. Banco de dados: %s", settings.DATABASE_URL)
    yield
    logger.info("Aplicacao finalizada.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "API REST academica para gerenciamento de tarefas, com persistencia "
        "em SQLite, desenvolvida para demonstrar hospedagem em uma Azure "
        "Virtual Machine."
    ),
    lifespan=lifespan,
)


# --------------------------------------------------------------------------
# Tratamento de erros
# --------------------------------------------------------------------------

@app.exception_handler(SQLAlchemyError)
async def erro_banco_handler(request, exc: SQLAlchemyError):
    """Evita expor detalhes internos do banco de dados ao cliente."""
    logger.exception("Erro de banco de dados ao processar %s %s", request.method, request.url)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erro interno ao acessar o banco de dados."},
    )


@app.exception_handler(Exception)
async def erro_generico_handler(request, exc: Exception):
    """Captura qualquer erro nao tratado e responde sem expor stack trace."""
    logger.exception("Erro nao tratado ao processar %s %s", request.method, request.url)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erro interno no servidor."},
    )


# --------------------------------------------------------------------------
# Health check
# --------------------------------------------------------------------------

@app.get(
    "/health",
    response_model=HealthOut,
    tags=["Health"],
    summary="Verifica a saude da aplicacao e a disponibilidade do banco",
)
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        database_status = "ok"
    except SQLAlchemyError:
        logger.exception("Falha ao verificar disponibilidade do banco de dados.")
        database_status = "falha"

    return HealthOut(
        status="ok" if database_status == "ok" else "degradado",
        database=database_status,
        version=settings.APP_VERSION,
    )


# --------------------------------------------------------------------------
# CRUD de tarefas
# --------------------------------------------------------------------------

@app.get(
    "/tarefas",
    response_model=TarefaListOut,
    tags=["Tarefas"],
    summary="Lista tarefas cadastradas, com paginacao",
)
def listar_tarefas(
    skip: int = Query(default=0, ge=0, description="Quantidade de registros a pular."),
    limit: int = Query(
        default=20, ge=1, le=settings.MAX_PAGE_SIZE, description="Quantidade maxima de registros retornados."
    ),
    db: Session = Depends(get_db),
):
    total = crud.contar_tarefas(db)
    itens = crud.listar_tarefas(db, skip=skip, limit=limit)
    return TarefaListOut(total=total, skip=skip, limit=limit, items=itens)


@app.get(
    "/tarefas/{tarefa_id}",
    response_model=TarefaOut,
    tags=["Tarefas"],
    summary="Consulta uma tarefa especifica",
    responses={404: {"model": ErroOut, "description": "Tarefa nao encontrada"}},
)
def obter_tarefa(tarefa_id: int, db: Session = Depends(get_db)):
    tarefa = crud.obter_tarefa(db, tarefa_id)
    if tarefa is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa nao encontrada.")
    return tarefa


@app.post(
    "/tarefas",
    response_model=TarefaOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Tarefas"],
    summary="Cadastra uma nova tarefa",
)
def criar_tarefa(dados: TarefaCreate, db: Session = Depends(get_db)):
    return crud.criar_tarefa(db, dados)


@app.put(
    "/tarefas/{tarefa_id}",
    response_model=TarefaOut,
    tags=["Tarefas"],
    summary="Atualiza uma tarefa existente",
    responses={404: {"model": ErroOut, "description": "Tarefa nao encontrada"}},
)
def atualizar_tarefa(tarefa_id: int, dados: TarefaUpdate, db: Session = Depends(get_db)):
    tarefa = crud.obter_tarefa(db, tarefa_id)
    if tarefa is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa nao encontrada.")
    return crud.atualizar_tarefa(db, tarefa, dados)


@app.delete(
    "/tarefas/{tarefa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Tarefas"],
    summary="Exclui uma tarefa existente",
    responses={404: {"model": ErroOut, "description": "Tarefa nao encontrada"}},
)
def excluir_tarefa(tarefa_id: int, db: Session = Depends(get_db)):
    tarefa = crud.obter_tarefa(db, tarefa_id)
    if tarefa is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa nao encontrada.")
    crud.excluir_tarefa(db, tarefa)
    return None
