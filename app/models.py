"""
Modelo de dados do SQLite.

Tabela `incidentes`: registro de incidentes de seguranca (ficticios, para
fins academicos). A tabela antiga `tarefas` (versao anterior do projeto)
NAO e removida nem alterada: `create_all` apenas cria tabelas ausentes.
"""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.enums import Categoria, Severidade, StatusIncidente, valores


def agora_utc() -> datetime:
    """Instante atual em UTC (armazenado sem fuso; a API serializa com 'Z')."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _in(coluna: str, enum_cls) -> str:
    return f"{coluna} IN ({', '.join(repr(v) for v in valores(enum_cls))})"


class Incidente(Base):
    __tablename__ = "incidentes"
    __table_args__ = (
        CheckConstraint(_in("severidade", Severidade), name="ck_incidentes_severidade"),
        CheckConstraint(_in("status", StatusIncidente), name="ck_incidentes_status"),
        CheckConstraint(_in("categoria", Categoria), name="ck_incidentes_categoria"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    categoria: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    severidade: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default=StatusIncidente.aberto.value, index=True)
    ip_origem: Mapped[str | None] = mapped_column(String(45), nullable=True)
    ativo_afetado: Mapped[str] = mapped_column(String(120), nullable=False)
    responsavel: Mapped[str | None] = mapped_column(String(80), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=agora_utc)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=agora_utc, onupdate=agora_utc)
    resolvido_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
