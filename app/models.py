"""Modelos ORM (SQLAlchemy) que definem as tabelas do banco de dados."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.config import settings
from app.database import Base


def _utcnow() -> datetime:
    """Retorna a data/hora atual em UTC (timezone-aware)."""
    return datetime.now(timezone.utc)


class Tarefa(Base):
    """Representa uma tarefa cadastrada pelo usuario."""

    __tablename__ = "tarefas"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    titulo = Column(String(settings.TITULO_MAX_LENGTH), nullable=False)
    descricao = Column(String(settings.DESCRICAO_MAX_LENGTH), nullable=True)
    concluida = Column(Boolean, nullable=False, default=False, server_default="0")
    criada_em = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    atualizada_em = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
