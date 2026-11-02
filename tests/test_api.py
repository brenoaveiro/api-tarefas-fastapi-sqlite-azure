"""
Suite de testes automatizados da API de Gerenciamento de Tarefas.

Cobre: health check, CRUD completo, validacoes, paginacao, codigos HTTP
e persistencia apos reabrir a conexao com o SQLite. Todos os testes usam
o banco isolado configurado em conftest.py.
"""

from app.database import SessionLocal
from app.models import Tarefa


def _criar_tarefa(client, titulo="Tarefa de teste", descricao="Descricao de teste", concluida=False):
    resposta = client.post(
        "/tarefas",
        json={"titulo": titulo, "descricao": descricao, "concluida": concluida},
    )
    return resposta


# --------------------------------------------------------------------------
# 1. Health check
# --------------------------------------------------------------------------

def test_health_check_retorna_ok(client):
    resposta = client.get("/health")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "ok"
    assert corpo["database"] == "ok"
    assert "version" in corpo


# --------------------------------------------------------------------------
# 2. Cadastro valido
# --------------------------------------------------------------------------

def test_criar_tarefa_valida_retorna_201(client):
    resposta = _criar_tarefa(client, titulo="Estudar Azure", descricao="Ler documentacao oficial.")
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["titulo"] == "Estudar Azure"
    assert corpo["descricao"] == "Ler documentacao oficial."
    assert corpo["concluida"] is False
    assert isinstance(corpo["id"], int)
    assert corpo["criada_em"] is not None
    assert corpo["atualizada_em"] is not None


# --------------------------------------------------------------------------
# 3. Validacao de cadastro invalido
# --------------------------------------------------------------------------

def test_criar_tarefa_sem_titulo_retorna_422(client):
    resposta = client.post("/tarefas", json={"descricao": "Falta o titulo"})
    assert resposta.status_code == 422


def test_criar_tarefa_titulo_vazio_retorna_422(client):
    resposta = client.post("/tarefas", json={"titulo": "", "descricao": "Titulo vazio"})
    assert resposta.status_code == 422


def test_criar_tarefa_titulo_muito_longo_retorna_422(client):
    resposta = client.post("/tarefas", json={"titulo": "a" * 500})
    assert resposta.status_code == 422


# --------------------------------------------------------------------------
# 4. Listagem sem tarefas
# --------------------------------------------------------------------------

def test_listar_tarefas_vazio(client):
    resposta = client.get("/tarefas")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["total"] == 0
    assert corpo["items"] == []


# --------------------------------------------------------------------------
# 5. Listagem com tarefas
# --------------------------------------------------------------------------

def test_listar_tarefas_com_registros(client):
    _criar_tarefa(client, titulo="Tarefa 1")
    _criar_tarefa(client, titulo="Tarefa 2")

    resposta = client.get("/tarefas")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["total"] == 2
    assert len(corpo["items"]) == 2
    # Ordem deterministica: por id ascendente.
    assert corpo["items"][0]["titulo"] == "Tarefa 1"
    assert corpo["items"][1]["titulo"] == "Tarefa 2"


# --------------------------------------------------------------------------
# 6. Paginacao
# --------------------------------------------------------------------------

def test_paginacao_limit_e_skip(client):
    for i in range(1, 6):
        _criar_tarefa(client, titulo=f"Tarefa {i}")

    resposta = client.get("/tarefas", params={"skip": 2, "limit": 2})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["total"] == 5
    assert corpo["skip"] == 2
    assert corpo["limit"] == 2
    assert len(corpo["items"]) == 2
    assert corpo["items"][0]["titulo"] == "Tarefa 3"
    assert corpo["items"][1]["titulo"] == "Tarefa 4"


def test_paginacao_parametros_invalidos_retorna_422(client):
    resposta_skip_negativo = client.get("/tarefas", params={"skip": -1})
    assert resposta_skip_negativo.status_code == 422

    resposta_limit_zero = client.get("/tarefas", params={"limit": 0})
    assert resposta_limit_zero.status_code == 422

    resposta_limit_excedido = client.get("/tarefas", params={"limit": 1000})
    assert resposta_limit_excedido.status_code == 422


# --------------------------------------------------------------------------
# 7. Consulta de ID existente
# --------------------------------------------------------------------------

def test_obter_tarefa_existente(client):
    criada = _criar_tarefa(client, titulo="Tarefa consultavel").json()

    resposta = client.get(f"/tarefas/{criada['id']}")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["id"] == criada["id"]
    assert corpo["titulo"] == "Tarefa consultavel"


# --------------------------------------------------------------------------
# 8. Consulta de ID inexistente
# --------------------------------------------------------------------------

def test_obter_tarefa_inexistente_retorna_404(client):
    resposta = client.get("/tarefas/99999")
    assert resposta.status_code == 404
    assert "detail" in resposta.json()


# --------------------------------------------------------------------------
# 9. Atualizacao valida
# --------------------------------------------------------------------------

def test_atualizar_tarefa_existente(client):
    criada = _criar_tarefa(client, titulo="Titulo original", descricao="Original").json()

    resposta = client.put(
        f"/tarefas/{criada['id']}",
        json={"titulo": "Titulo atualizado", "descricao": "Atualizada", "concluida": True},
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["titulo"] == "Titulo atualizado"
    assert corpo["descricao"] == "Atualizada"
    assert corpo["concluida"] is True
    assert corpo["atualizada_em"] >= corpo["criada_em"]


def test_atualizar_tarefa_com_dados_invalidos_retorna_422(client):
    criada = _criar_tarefa(client).json()

    resposta = client.put(f"/tarefas/{criada['id']}", json={"descricao": "Sem titulo"})
    assert resposta.status_code == 422


# --------------------------------------------------------------------------
# 10. Atualizacao de ID inexistente
# --------------------------------------------------------------------------

def test_atualizar_tarefa_inexistente_retorna_404(client):
    resposta = client.put(
        "/tarefas/99999",
        json={"titulo": "Nao existe", "descricao": None, "concluida": False},
    )
    assert resposta.status_code == 404


# --------------------------------------------------------------------------
# 11. Exclusao valida
# --------------------------------------------------------------------------

def test_excluir_tarefa_existente(client):
    criada = _criar_tarefa(client).json()

    resposta = client.delete(f"/tarefas/{criada['id']}")
    assert resposta.status_code == 204
    assert resposta.content == b""

    resposta_get = client.get(f"/tarefas/{criada['id']}")
    assert resposta_get.status_code == 404


# --------------------------------------------------------------------------
# 12. Exclusao de ID inexistente
# --------------------------------------------------------------------------

def test_excluir_tarefa_inexistente_retorna_404(client):
    resposta = client.delete("/tarefas/99999")
    assert resposta.status_code == 404


# --------------------------------------------------------------------------
# 13. Persistencia apos reabrir a conexao com o SQLite
# --------------------------------------------------------------------------

def test_persistencia_apos_reabrir_conexao(client):
    criada = _criar_tarefa(client, titulo="Tarefa persistente").json()

    # Fecha a sessao atual e abre uma conexao totalmente nova com o
    # mesmo arquivo .db, simulando uma reinicializacao da aplicacao.
    nova_sessao = SessionLocal()
    try:
        tarefa_no_banco = nova_sessao.query(Tarefa).filter(Tarefa.id == criada["id"]).first()
        assert tarefa_no_banco is not None
        assert tarefa_no_banco.titulo == "Tarefa persistente"
    finally:
        nova_sessao.close()


# --------------------------------------------------------------------------
# 14. Schemas JSON consistentes
# --------------------------------------------------------------------------

def test_schema_tarefa_contem_todos_os_campos(client):
    criada = _criar_tarefa(client).json()
    campos_esperados = {"id", "titulo", "descricao", "concluida", "criada_em", "atualizada_em"}
    assert campos_esperados.issubset(criada.keys())


def test_schema_listagem_contem_envelope_consistente(client):
    _criar_tarefa(client)
    resposta = client.get("/tarefas")
    corpo = resposta.json()
    assert {"total", "skip", "limit", "items"}.issubset(corpo.keys())
