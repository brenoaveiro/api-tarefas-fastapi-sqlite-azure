"""
Schemas Pydantic: definem o formato (e as validacoes) dos dados que
entram e saem da API. Mantidos separados dos modelos ORM (models.py)
para que a representacao HTTP da tarefa possa evoluir independentemente
da estrutura interna de persistencia.
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field

from app.config import settings


class TarefaBase(BaseModel):
    titulo: str = Field(
        ...,
        min_length=1,
        max_length=settings.TITULO_MAX_LENGTH,
        description="Titulo da tarefa (obrigatorio).",
        examples=["Estudar para a prova de Redes"],
    )
    descricao: str | None = Field(
        default=None,
        max_length=settings.DESCRICAO_MAX_LENGTH,
        description="Descricao detalhada da tarefa (opcional).",
        examples=["Revisar o capitulo 4 do livro antes de sexta-feira."],
    )


class TarefaCreate(TarefaBase):
    """Dados aceitos ao criar uma tarefa (POST /tarefas)."""

    concluida: bool = Field(
        default=False, description="Estado inicial de conclusao da tarefa."
    )


class TarefaUpdate(TarefaBase):
    """Dados aceitos ao atualizar uma tarefa (PUT /tarefas/{id})."""

    concluida: bool = Field(
        default=False, description="Estado de conclusao da tarefa."
    )


class TarefaOut(TarefaBase):
    """Dados retornados pela API para uma tarefa."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Identificador unico da tarefa.")
    concluida: bool
    criada_em: datetime = Field(..., description="Data/hora de criacao, em UTC.")
    atualizada_em: datetime = Field(
        ..., description="Data/hora da ultima atualizacao, em UTC."
    )


class TarefaListOut(BaseModel):
    """Envelope de resposta para listagem paginada de tarefas."""

    total: int = Field(..., description="Quantidade total de tarefas cadastradas.")
    skip: int = Field(..., description="Quantidade de registros pulados (offset).")
    limit: int = Field(..., description="Quantidade maxima de registros retornados.")
    items: List[TarefaOut] = Field(..., description="Tarefas da pagina atual.")


class HealthOut(BaseModel):
    """Resposta do endpoint de health check."""

    status: str = Field(..., examples=["ok"])
    database: str = Field(..., examples=["ok"])
    version: str = Field(..., examples=["1.0.0"])


class ErroOut(BaseModel):
    """Formato padronizado de erro retornado pela API."""

    detail: str = Field(..., examples=["Tarefa nao encontrada."])
