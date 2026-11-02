"""Esquemas Pydantic (validacao de entrada e formato de saida) da CyberIncident API."""

import ipaddress
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.enums import Categoria, Severidade, StatusIncidente


def _limpar(valor):
    if isinstance(valor, str):
        valor = valor.strip()
        return valor or None
    return valor


class _Base(BaseModel):
    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)

    @field_validator("ip_origem", "responsavel", mode="before", check_fields=False)
    @classmethod
    def _vazio_vira_none(cls, v):
        return _limpar(v)

    @field_validator("ip_origem", check_fields=False)
    @classmethod
    def _validar_ip(cls, v):
        if v is None:
            return v
        try:
            return str(ipaddress.ip_address(v))
        except ValueError as exc:
            raise ValueError("ip_origem invalido: informe um IPv4 ou IPv6 valido") from exc


class IncidenteCreate(_Base):
    titulo: str = Field(min_length=3, max_length=200, examples=["[DEMO] Tentativas de login repetidas no servidor web"])
    descricao: str = Field(min_length=5, max_length=2000,
                           examples=["Registro ficticio: 50 tentativas de autenticacao falhas em 2 minutos."])
    categoria: Categoria = Field(examples=["forca_bruta"])
    severidade: Severidade = Field(examples=["alta"])
    ip_origem: Optional[str] = Field(default=None, examples=["203.0.113.25"])
    ativo_afetado: str = Field(min_length=1, max_length=120, examples=["srv-web-01"])
    responsavel: Optional[str] = Field(default=None, max_length=80, examples=["Analista N1"])


class IncidenteUpdate(IncidenteCreate):
    """Atualizacao completa (PUT): todos os campos, mais o status."""
    status: StatusIncidente = Field(examples=["em_analise"])


class StatusUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    status: StatusIncidente = Field(examples=["contido"])


class IncidenteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    descricao: str
    categoria: str
    severidade: str
    status: str
    ip_origem: Optional[str] = None
    ativo_afetado: str
    responsavel: Optional[str] = None
    criado_em: datetime
    atualizado_em: datetime
    resolvido_em: Optional[datetime] = None

    @field_serializer("criado_em", "atualizado_em", "resolvido_em")
    def _utc(self, v: Optional[datetime]):
        if v is None:
            return None
        return v.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class IncidenteListOut(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[IncidenteOut]


class EstatisticasOut(BaseModel):
    total: int
    por_status: dict[str, int]
    por_severidade: dict[str, int]
    por_categoria: dict[str, int]


class HealthOut(BaseModel):
    status: str
    database: str
    version: str


class ErroOut(BaseModel):
    detail: str
