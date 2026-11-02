"""Operacoes de banco de dados (camada de persistencia). Somente consultas parametrizadas via ORM."""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import TRANSICOES, Categoria, Severidade, StatusIncidente, valores
from app.models import Incidente, agora_utc
from app.schemas import IncidenteCreate, IncidenteUpdate


class TransicaoInvalida(ValueError):
    """Mudança de status não permitida pelo fluxo de tratamento."""


def listar(db: Session, skip: int, limit: int, severidade: Optional[str] = None,
           status: Optional[str] = None, categoria: Optional[str] = None):
    filtros = []
    if severidade:
        filtros.append(Incidente.severidade == severidade)
    if status:
        filtros.append(Incidente.status == status)
    if categoria:
        filtros.append(Incidente.categoria == categoria)
    total = db.scalar(select(func.count()).select_from(Incidente).where(*filtros)) or 0
    itens = db.scalars(
        select(Incidente).where(*filtros).order_by(Incidente.criado_em.desc(), Incidente.id.desc())
        .offset(skip).limit(limit)
    ).all()
    return total, itens


def obter(db: Session, incidente_id: int) -> Optional[Incidente]:
    return db.get(Incidente, incidente_id)


def criar(db: Session, dados: IncidenteCreate) -> Incidente:
    inc = Incidente(**dados.model_dump(), status=StatusIncidente.aberto.value)
    db.add(inc)
    db.commit()
    db.refresh(inc)
    return inc


def _aplicar_status(inc: Incidente, novo: str) -> None:
    """Valida a transicao e mantem `resolvido_em` coerente (preenche ao resolver, limpa ao reabrir)."""
    atual = StatusIncidente(inc.status)
    alvo = StatusIncidente(novo)
    if alvo == atual:
        return
    if alvo not in TRANSICOES[atual]:
        permitidos = ", ".join(sorted(s.value for s in TRANSICOES[atual]))
        raise TransicaoInvalida(f"Transição de status inválida: {atual.value} -> {alvo.value}. Permitidas: {permitidos}.")
    inc.status = alvo.value
    inc.resolvido_em = agora_utc() if alvo == StatusIncidente.resolvido else None


def atualizar(db: Session, inc: Incidente, dados: IncidenteUpdate) -> Incidente:
    novos = dados.model_dump()
    novo_status = novos.pop("status")
    _aplicar_status(inc, novo_status)  # valida antes de alterar qualquer campo
    for campo, valor in novos.items():
        setattr(inc, campo, valor)
    db.commit()
    db.refresh(inc)
    return inc


def alterar_status(db: Session, inc: Incidente, novo_status: str) -> Incidente:
    _aplicar_status(inc, novo_status)
    db.commit()
    db.refresh(inc)
    return inc


def excluir(db: Session, inc: Incidente) -> None:
    db.delete(inc)
    db.commit()


def _contagem(db: Session, coluna, esperados: list[str]) -> dict[str, int]:
    base = {v: 0 for v in esperados}
    for valor, qtd in db.execute(select(coluna, func.count()).group_by(coluna)).all():
        base[valor] = qtd
    return base


def estatisticas(db: Session) -> dict:
    """Contagens reais calculadas no SQLite (GROUP BY), com zeros para valores sem registros."""
    return {
        "total": db.scalar(select(func.count()).select_from(Incidente)) or 0,
        "por_status": _contagem(db, Incidente.status, valores(StatusIncidente)),
        "por_severidade": _contagem(db, Incidente.severidade, valores(Severidade)),
        "por_categoria": _contagem(db, Incidente.categoria, valores(Categoria)),
    }
