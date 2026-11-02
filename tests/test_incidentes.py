"""Testes da CyberIncident API (banco SQLite isolado, ver conftest.py)."""

import re
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app import crud
from app.database import Base, get_db
from app.main import app
import app.models as _modelos  # noqa: F401  (registra a tabela no metadata)

RAIZ = Path(__file__).resolve().parent.parent


def novo(**extra):
    d = {"titulo": "[TESTE] Tentativas de login", "descricao": "Registro ficticio de teste.",
         "categoria": "forca_bruta", "severidade": "alta", "ip_origem": "203.0.113.10",
         "ativo_afetado": "srv-web-01", "responsavel": "Analista N1"}
    d.update(extra)
    return d


def criar(client, **extra):
    r = client.post("/incidentes", json=novo(**extra))
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------- 1-2 basico
def test_inicializacao_e_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok", "version": "2.0.0"}


def test_health_degradado_quando_banco_falha(client):
    class Quebrado:
        def execute(self, *a, **k):
            raise SQLAlchemyError("falha simulada")

    def quebrado():
        yield Quebrado()

    app.dependency_overrides[get_db] = quebrado
    try:
        r = client.get("/health")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503 and r.json()["database"] == "erro"
    assert "falha simulada" not in r.text


# --------------------------------------------------------------------- CRUD
def test_criar_incidente(client):
    inc = criar(client)
    assert inc["id"] >= 1 and inc["status"] == "aberto"
    assert inc["resolvido_em"] is None
    assert inc["criado_em"].endswith("Z") and inc["atualizado_em"].endswith("Z")
    assert inc["ip_origem"] == "203.0.113.10"


def test_obter_por_id_e_404(client):
    inc = criar(client)
    assert client.get(f"/incidentes/{inc['id']}").json()["titulo"] == inc["titulo"]
    r = client.get("/incidentes/99999")
    assert r.status_code == 404 and r.json()["detail"] == "Incidente nao encontrado."


def test_listagem_paginada_e_filtros(client):
    for i in range(5):
        criar(client, titulo=f"[TESTE] incidente {i}", severidade="critica" if i < 2 else "baixa",
              categoria="phishing" if i % 2 else "malware")
    r = client.get("/incidentes?limit=2&skip=2").json()
    assert r["total"] == 5 and len(r["items"]) == 2 and r["skip"] == 2 and r["limit"] == 2
    assert client.get("/incidentes?severidade=critica").json()["total"] == 2
    assert client.get("/incidentes?categoria=phishing").json()["total"] == 2
    assert client.get("/incidentes?status=resolvido").json()["total"] == 0
    # ordenacao: mais recente primeiro
    ids = [i["id"] for i in client.get("/incidentes").json()["items"]]
    assert ids == sorted(ids, reverse=True)


def test_atualizacao_completa(client):
    inc = criar(client)
    corpo = novo(titulo="[TESTE] titulo novo", severidade="critica", status="em_analise", responsavel="Analista N2")
    r = client.put(f"/incidentes/{inc['id']}", json=corpo)
    assert r.status_code == 200
    j = r.json()
    assert j["titulo"] == "[TESTE] titulo novo" and j["severidade"] == "critica" and j["status"] == "em_analise"
    assert client.put("/incidentes/99999", json=corpo).status_code == 404


def test_put_com_transicao_invalida_nao_altera_nada(client):
    inc = criar(client)
    r = client.put(f"/incidentes/{inc['id']}", json=novo(titulo="[TESTE] nao deve gravar", status="resolvido"))
    assert r.status_code == 422
    assert client.get(f"/incidentes/{inc['id']}").json()["titulo"] == inc["titulo"]


def test_alterar_status_e_datas_de_resolucao(client):
    inc = criar(client)
    url = f"/incidentes/{inc['id']}/status"
    assert client.patch(url, json={"status": "em_analise"}).json()["status"] == "em_analise"
    assert client.patch(url, json={"status": "contido"}).json()["status"] == "contido"
    r = client.patch(url, json={"status": "resolvido"}).json()
    assert r["status"] == "resolvido" and r["resolvido_em"] is not None
    r = client.patch(url, json={"status": "aberto"}).json()          # reabertura
    assert r["status"] == "aberto" and r["resolvido_em"] is None
    assert client.patch(url, json={"status": "aberto"}).status_code == 200   # mesmo status: idempotente


def test_transicao_invalida_e_404_no_patch(client):
    inc = criar(client)
    r = client.patch(f"/incidentes/{inc['id']}/status", json={"status": "resolvido"})
    assert r.status_code == 422 and "invalida" in r.json()["detail"]
    assert client.patch("/incidentes/99999/status", json={"status": "em_analise"}).status_code == 404


def test_excluir(client):
    inc = criar(client)
    assert client.delete(f"/incidentes/{inc['id']}").status_code == 204
    assert client.get(f"/incidentes/{inc['id']}").status_code == 404
    assert client.delete(f"/incidentes/{inc['id']}").status_code == 404


# ------------------------------------------------------------- validacoes
@pytest.mark.parametrize("campo,valor", [("severidade", "extrema"), ("categoria", "ransomware"), ("status", "x")])
def test_valores_invalidos_422(client, campo, valor):
    if campo == "status":
        inc = criar(client)
        assert client.patch(f"/incidentes/{inc['id']}/status", json={"status": valor}).status_code == 422
    else:
        assert client.post("/incidentes", json=novo(**{campo: valor})).status_code == 422
    assert client.get(f"/incidentes?{campo}={valor}").status_code == 422


@pytest.mark.parametrize("ip", ["999.1.1.1", "abc", "203.0.113", "1.2.3.4.5"])
def test_ip_invalido(client, ip):
    assert client.post("/incidentes", json=novo(ip_origem=ip)).status_code == 422


def test_ip_valido_ipv6_e_vazio(client):
    assert criar(client, ip_origem="2001:db8::1")["ip_origem"] == "2001:db8::1"
    assert criar(client, ip_origem="")["ip_origem"] is None
    assert criar(client, ip_origem=None, responsavel="  ")["responsavel"] is None


@pytest.mark.parametrize("campo", ["titulo", "descricao", "categoria", "severidade", "ativo_afetado"])
def test_campos_obrigatorios(client, campo):
    corpo = novo()
    corpo.pop(campo)
    assert client.post("/incidentes", json=corpo).status_code == 422


def test_titulo_curto_e_id_invalido(client):
    assert client.post("/incidentes", json=novo(titulo="ab")).status_code == 422
    assert client.get("/incidentes/abc").status_code == 422


# ------------------------------------------------------------ estatisticas
def test_estatisticas_banco_vazio(client):
    r = client.get("/incidentes/estatisticas")
    assert r.status_code == 200          # nao e confundida com /incidentes/{id}
    j = r.json()
    assert j["total"] == 0
    assert set(j["por_status"]) == {"aberto", "em_analise", "contido", "resolvido"}
    assert set(j["por_severidade"]) == {"baixa", "media", "alta", "critica"}
    assert set(j["por_categoria"]) >= {"phishing", "malware", "forca_bruta", "outros"}
    assert sum(j["por_status"].values()) == 0


def test_estatisticas_por_severidade_status_categoria(client):
    criar(client, severidade="critica", categoria="malware")
    criar(client, severidade="critica", categoria="phishing")
    criar(client, severidade="media", categoria="phishing")
    b = criar(client, severidade="baixa", categoria="outros")
    client.patch(f"/incidentes/{b['id']}/status", json={"status": "em_analise"})
    client.patch(f"/incidentes/{b['id']}/status", json={"status": "resolvido"})
    j = client.get("/incidentes/estatisticas").json()
    assert j["total"] == 4
    assert j["por_severidade"] == {"baixa": 1, "media": 1, "alta": 0, "critica": 2}
    assert j["por_status"] == {"aberto": 3, "em_analise": 0, "contido": 0, "resolvido": 1}
    assert j["por_categoria"]["phishing"] == 2 and j["por_categoria"]["malware"] == 1
    assert sum(j["por_categoria"].values()) == 4


# ------------------------------------------------------------- persistencia
def test_persistencia_apos_reabrir_o_banco(client):
    from app.database import engine
    inc = criar(client, titulo="[TESTE] persistente")
    url = engine.url.render_as_string(hide_password=False)
    outro = create_engine(url)                      # nova conexao/engine, como apos reiniciar o servico
    with outro.connect() as c:
        titulo = c.execute(text("SELECT titulo FROM incidentes WHERE id=:i"), {"i": inc["id"]}).scalar()
    outro.dispose()
    assert titulo == "[TESTE] persistente"


def test_migracao_preserva_tabela_antiga_e_e_repetivel(tmp_path):
    caminho = tmp_path / "legado.db"
    con = sqlite3.connect(caminho)
    con.execute("CREATE TABLE tarefas (id INTEGER PRIMARY KEY, titulo TEXT)")
    con.execute("INSERT INTO tarefas (titulo) VALUES ('tarefa antiga')")
    con.commit()
    con.close()
    eng = create_engine(f"sqlite:///{caminho.as_posix()}")
    for _ in range(2):                              # repetivel
        Base.metadata.create_all(bind=eng)
    assert "incidentes" in inspect(eng).get_table_names() and "tarefas" in inspect(eng).get_table_names()
    with eng.connect() as c:
        assert c.execute(text("SELECT titulo FROM tarefas")).scalar() == "tarefa antiga"
        assert c.execute(text("SELECT count(*) FROM incidentes")).scalar() == 0
    eng.dispose()


def test_check_constraints_do_banco():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(bind=eng)
    with eng.begin() as c, pytest.raises(Exception):
        c.execute(text("INSERT INTO incidentes (titulo,descricao,categoria,severidade,status,ativo_afetado,criado_em,atualizado_em) "
                       "VALUES ('t','d','phishing','extrema','aberto','a','2026-01-01','2026-01-01')"))


# ------------------------------------------------------ interface e Swagger
def test_openapi(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    j = r.json()
    assert j["info"]["title"] == "CyberIncident API"
    for p in ("/health", "/incidentes", "/incidentes/estatisticas", "/incidentes/{incidente_id}",
              "/incidentes/{incidente_id}/status"):
        assert p in j["paths"]
    assert {t["name"] for t in j["tags"]} == {"Sistema", "Incidentes", "Estatisticas"}
    assert "/tarefas" not in j["paths"]


def test_dashboard_e_assets(client):
    r = client.get("/")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert "CyberIncident API" in r.text and "Content-Security-Policy" in r.headers
    assert "<script>" not in r.text                       # sem script inline (compativel com a CSP)
    for url in ("/static/dashboard.css", "/static/dashboard.js", "/static/favicon.svg", "/static/swagger-tema.css",
                "/static/swagger-tema.js", "/static/swagger/swagger-ui-bundle.js", "/static/swagger/swagger-ui.css"):
        assert client.get(url).status_code == 200, url


def test_swagger_personalizado_sem_cdn(client):
    r = client.get("/docs")
    assert r.status_code == 200
    assert "/static/swagger/swagger-ui-bundle.js" in r.text and "swagger-tema.css" in r.text
    assert "cdn.jsdelivr.net" not in r.text and "unpkg.com" not in r.text


def test_dashboard_js_nao_usa_innerhtml():
    js = (RAIZ / "app/static/dashboard.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js and "insertAdjacentHTML" not in js and "document.write" not in js


def test_xss_armazenado_como_texto(client):
    inc = criar(client, titulo="<script>alert(1)</script>")
    assert client.get(f"/incidentes/{inc['id']}").json()["titulo"] == "<script>alert(1)</script>"
    assert "application/json" in client.get(f"/incidentes/{inc['id']}").headers["content-type"]


def test_sql_injection_nao_altera_consultas(client):
    criar(client)
    r = client.get("/incidentes", params={"severidade": "alta' OR '1'='1"})
    assert r.status_code == 422
    inc = criar(client, titulo="x'); DROP TABLE incidentes;--")
    assert client.get("/incidentes").json()["total"] == 2 and inc["id"]


def test_erro_interno_nao_vaza_detalhes(monkeypatch):
    def quebra(*a, **k):
        raise RuntimeError("segredo-interno /var/lib/x")
    monkeypatch.setattr(crud, "listar", quebra)
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/incidentes")
    assert r.status_code == 500 and "segredo-interno" not in r.text and "Traceback" not in r.text


def test_sem_cors_aberto(client):
    r = client.get("/incidentes", headers={"Origin": "https://exemplo.invalid"})
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


# ------------------------------------------- compatibilidade e regressao
def test_configuracao_compativel_com_systemd_e_env():
    svc = (RAIZ / "deploy/systemd/api-tarefas.service").read_text(encoding="utf-8")
    assert "app.main:app" in svc and "--host 127.0.0.1" in svc and "0.0.0.0" not in svc
    assert "EnvironmentFile=/opt/api-tarefas/.env" in svc and "ReadWritePaths=/var/lib/api-tarefas" in svc
    env = (RAIZ / ".env.example").read_text(encoding="utf-8")
    assert re.search(r"^APP_NAME=CyberIncident API$", env, re.M)
    for chave in ("DATABASE_URL", "SEED_DEMO_DATA", "MAX_PAGE_SIZE"):
        assert chave in env


def test_protecao_de_escrita_do_nginx_preservada():
    conf = (RAIZ / "deploy/nginx/api-tarefas.conf").read_text(encoding="utf-8")
    assert "limit_except GET HEAD OPTIONS" in conf and "deny all;" in conf
    assert "api-tarefas-writers" in conf and "proxy_pass http://127.0.0.1:8000" in conf
    assert "listen 8000" not in conf


def test_gitignore_protege_banco_e_segredos():
    g = (RAIZ / ".gitignore").read_text(encoding="utf-8")
    for padrao in (".env", "*.db", "*.pem", "*.key"):
        assert padrao in g
