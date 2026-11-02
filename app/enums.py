"""Valores permitidos para os campos classificatorios dos incidentes."""

from enum import Enum


class Severidade(str, Enum):
    baixa = "baixa"
    media = "media"
    alta = "alta"
    critica = "critica"


class StatusIncidente(str, Enum):
    aberto = "aberto"
    em_analise = "em_analise"
    contido = "contido"
    resolvido = "resolvido"


class Categoria(str, Enum):
    phishing = "phishing"
    malware = "malware"
    acesso_indevido = "acesso_indevido"
    forca_bruta = "forca_bruta"
    vazamento_dados = "vazamento_dados"
    anomalia_rede = "anomalia_rede"
    outros = "outros"


# Transicoes de status permitidas (fluxo de tratamento de um incidente).
# "resolvido -> aberto" representa a reabertura do incidente.
TRANSICOES = {
    StatusIncidente.aberto: {StatusIncidente.em_analise},
    StatusIncidente.em_analise: {StatusIncidente.contido, StatusIncidente.resolvido},
    StatusIncidente.contido: {StatusIncidente.em_analise, StatusIncidente.resolvido},
    StatusIncidente.resolvido: {StatusIncidente.aberto},
}


def valores(enum_cls) -> list[str]:
    return [e.value for e in enum_cls]
