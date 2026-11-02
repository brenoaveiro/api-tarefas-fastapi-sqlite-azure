"""
Configuracao da conexao com o banco de dados SQLite via SQLAlchemy.

SQLite armazena todo o banco em um unico arquivo no disco. Isso o torna
ideal para um projeto academico pequeno: nao exige um servidor de banco
de dados separado, nao gera custo adicional de infraestrutura e e
suficiente para o volume de dados e de acessos simultaneos deste
trabalho. Ele nao deve ser confundido com um banco de dados gerenciado
de producao (como Azure SQL Database): nao possui replicacao, nao lida
bem com alta concorrencia de escrita e nao e a escolha recomendada para
uma aplicacao real de grande escala.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

database_url = settings.DATABASE_URL

# Garante que o diretorio onde o arquivo .db sera criado ja existe
# (relevante tanto em desenvolvimento ./data quanto em produção
# /var/lib/api-tarefas).
if database_url.startswith("sqlite:///"):
    db_path = database_url.replace("sqlite:///", "", 1)
    db_dir = os.path.dirname(db_path)
    if db_dir:
        Path(db_dir).mkdir(parents=True, exist_ok=True)

# `check_same_thread=False` e necessario porque o Uvicorn pode atender
# requisicoes em threads diferentes da thread que criou a conexao.
# O SQLAlchemy ainda assim controla o acesso por sessao, evitando
# corrupcao do arquivo.
engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    """Ativa WAL (Write-Ahead Logging) para reduzir bloqueios entre
    leituras e escritas concorrentes, e habilita chaves estrangeiras."""
    if database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency do FastAPI: fornece uma sessao por requisicao e garante
    o fechamento correto, mesmo em caso de erro."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
