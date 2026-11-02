"""
Configuracoes centrais da aplicacao.

Todas as configuracoes sao lidas de variaveis de ambiente, com valores
padrao seguros para desenvolvimento local. Em produção (VM Azure), os
valores reais devem ser definidos em um arquivo `.env` (nao versionado)
ou diretamente nas variaveis de ambiente do systemd.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _str_to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Agrupa todas as configuracoes da aplicacao."""

    # Nome e versao exibidos na documentacao Swagger.
    APP_NAME: str = os.getenv("APP_NAME", "CyberIncident API")
    APP_VERSION: str = os.getenv("APP_VERSION", "2.0.0")

    # Caminho do banco SQLite. Em desenvolvimento, fica dentro do projeto,
    # em ./data/tarefas.db (fora do controle de versao, ver .gitignore).
    # Em produção, deve apontar para um diretorio persistente da VM,
    # como /var/lib/api-tarefas/tarefas.db.
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{(BASE_DIR / 'data' / 'tarefas.db').as_posix()}",
    )

    # Quando verdadeiro, popula o banco com tarefas de exemplo na primeira
    # inicializacao (banco vazio). Util para demonstracoes.
    SEED_DEMO_DATA: bool = _str_to_bool(os.getenv("SEED_DEMO_DATA", "false"))

    # Tamanho maximo de pagina na listagem paginada.
    MAX_PAGE_SIZE: int = int(os.getenv("MAX_PAGE_SIZE", "100"))

    # Tamanho maximo do titulo da tarefa.
    TITULO_MAX_LENGTH: int = int(os.getenv("TITULO_MAX_LENGTH", "200"))

    # Tamanho maximo da descricao da tarefa.
    DESCRICAO_MAX_LENGTH: int = int(os.getenv("DESCRICAO_MAX_LENGTH", "2000"))


settings = Settings()
