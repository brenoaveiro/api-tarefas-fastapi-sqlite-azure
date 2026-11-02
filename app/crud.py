"""
Camada de acesso a dados (CRUD). Isola as operacoes de banco de dados
dos endpoints HTTP definidos em main.py, para manter responsabilidades
separadas e facilitar testes.
"""

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Tarefa
from app.schemas import TarefaCreate, TarefaUpdate


def contar_tarefas(db: Session) -> int:
    return db.query(func.count(Tarefa.id)).scalar() or 0


def listar_tarefas(db: Session, skip: int, limit: int) -> list[Tarefa]:
    """Lista tarefas em ordem deterministica (por id ascendente)."""
    return (
        db.query(Tarefa)
        .order_by(Tarefa.id.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def obter_tarefa(db: Session, tarefa_id: int) -> Tarefa | None:
    return db.query(Tarefa).filter(Tarefa.id == tarefa_id).first()


def criar_tarefa(db: Session, dados: TarefaCreate) -> Tarefa:
    agora = datetime.now(timezone.utc)
    tarefa = Tarefa(
        titulo=dados.titulo,
        descricao=dados.descricao,
        concluida=dados.concluida,
        criada_em=agora,
        atualizada_em=agora,
    )
    db.add(tarefa)
    db.commit()
    db.refresh(tarefa)
    return tarefa


def atualizar_tarefa(db: Session, tarefa: Tarefa, dados: TarefaUpdate) -> Tarefa:
    tarefa.titulo = dados.titulo
    tarefa.descricao = dados.descricao
    tarefa.concluida = dados.concluida
    tarefa.atualizada_em = datetime.now(timezone.utc)
    db.add(tarefa)
    db.commit()
    db.refresh(tarefa)
    return tarefa


def excluir_tarefa(db: Session, tarefa: Tarefa) -> None:
    db.delete(tarefa)
    db.commit()
