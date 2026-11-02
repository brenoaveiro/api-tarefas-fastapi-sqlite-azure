"""
Configuracao compartilhada dos testes.

Usa um banco SQLite totalmente isolado, em um diretorio temporario
exclusivo da sessao de testes, para garantir que os testes nunca leiam
ou apaguem o banco de desenvolvimento/producao real.

A variavel de ambiente DATABASE_URL e definida ANTES de qualquer import
dos modulos da aplicacao, para que o engine do SQLAlchemy seja criado
apontando desde o inicio para o banco de teste.
"""

import os
import tempfile
from pathlib import Path

_tmp_dir = tempfile.mkdtemp(prefix="api_tarefas_test_")
_db_path = Path(_tmp_dir) / "test_tarefas.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path.as_posix()}"
os.environ["SEED_DEMO_DATA"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

TEST_DATABASE_URL = os.environ["DATABASE_URL"]


@pytest.fixture(autouse=True)
def banco_limpo():
    """Garante um banco de dados vazio e com o schema atualizado antes
    de cada teste, mantendo os testes independentes entre si."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def client():
    """Cliente de teste HTTP (TestClient usa HTTPX internamente)."""
    with TestClient(app) as test_client:
        yield test_client
