"""
Testes das funcoes de leitura/validacao do .env em deploy/install.sh.

O install.sh pode ser carregado com `source` sem executar a instalacao
(so roda `main` quando executado diretamente). Aqui garantimos que o .env
e tratado como DADO (nunca executado como Bash) e que os valores lidos sao
os mesmos que o systemd entregaria a app/config.py.

Os testes sao ignorados se nao houver um Bash utilizavel (ex.: Windows sem
Git Bash). O conteudo do .env e criado dentro do proprio Bash, assim nao ha
problema de conversao de caminhos entre Windows e Linux.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
BASH = shutil.which("bash")


def _bash_ok() -> bool:
    if not BASH:
        return False
    try:
        r = subprocess.run(
            [BASH, "-c", '(( BASH_VERSINFO[0] >= 4 )) && echo ok'],
            capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return r.stdout.strip() == "ok"


pytestmark = pytest.mark.skipif(not _bash_ok(), reason="Bash 4+ nao disponivel")


def bash(script: str, env_text: str | None = None):
    """Roda `script` com install.sh carregado. Se `env_text` for dado, ele
    e gravado em $ENVF (arquivo temporario criado pelo proprio Bash)."""
    prelude = 'source deploy/install.sh; ENVF="$(mktemp)"; trap \'rm -f "$ENVF"\' EXIT\n'
    if env_text is not None:
        prelude += 'printf "%s" "$ENV_TEXT" > "$ENVF"\n'
    import os
    env = {**os.environ, "ENV_TEXT": env_text or ""}
    return subprocess.run(
        [BASH, "-c", prelude + script],
        cwd=RAIZ, env=env, capture_output=True, text=True, timeout=60,
    )


def test_install_sh_tem_sintaxe_valida_e_nao_executa_ao_ser_carregado():
    r = subprocess.run([BASH, "-n", "deploy/install.sh"], cwd=RAIZ, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert bash("echo carregado").stdout.strip() == "carregado"


def test_scripts_usam_fim_de_linha_lf():
    for nome in ("install.sh", "deploy.sh", "backup.sh"):
        assert b"\r" not in (RAIZ / "deploy" / nome).read_bytes(), nome


def test_valor_com_espacos_nao_e_executado_como_comando():
    # Com `source .env` isto tentaria rodar o comando "de" e "dados".
    r = bash(
        'env_get "$ENVF" APP_NAME',
        "APP_NAME=CyberIncident API\nTITULO=oi $(touch /tmp/pwned) `id`\n",
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout == "CyberIncident API"
    r = bash('env_get "$ENVF" TITULO', "TITULO=oi $(touch /tmp/pwned) `id`; rm -rf x\n")
    assert r.stdout == "oi $(touch /tmp/pwned) `id`; rm -rf x"


def test_regras_do_systemd_aspas_comentarios_crlf_e_ultima_atribuicao():
    texto = (
        "# comentario\r\n"
        "; outro comentario\r\n"
        "  A=  com espacos nas pontas  \r\n"
        'B="entre aspas duplas"\n'
        "C='entre aspas simples'\n"
        "D=valor # nao e comentario\n"
        "E=primeiro\n"
        "E=segundo\n"
        "F=\n"
        "G=a=b=c\n"
        "$HOME=ignorado\n"
    )
    esperado = {
        "A": "com espacos nas pontas",
        "B": "entre aspas duplas",
        "C": "entre aspas simples",
        "D": "valor # nao e comentario",
        "E": "segundo",
        "F": "",
        "G": "a=b=c",
    }
    for chave, valor in esperado.items():
        r = bash(f'env_get "$ENVF" {chave}', texto)
        assert r.returncode == 0, (chave, r.stderr)
        assert r.stdout == valor, chave
    assert bash('env_get "$ENVF" HOME', texto).returncode == 1
    assert bash('env_get "$ENVF" AUSENTE', texto).returncode == 1


def test_env_example_e_valido_apos_ajuste_do_banco_e_compativel_com_config():
    exemplo = (RAIZ / ".env.example").read_text(encoding="utf-8")
    r = bash(
        'env_set "$ENVF" DATABASE_URL "$DB_URL"\n'
        'validate_env_file "$ENVF" && echo VALIDO\n'
        'echo "URL=$(env_get "$ENVF" DATABASE_URL)"\n'
        'echo "NOME=$(env_get "$ENVF" APP_NAME)"\n'
        'grep -c "^DATABASE_URL=" "$ENVF"',
        exemplo,
    )
    assert r.returncode == 0, r.stderr
    saida = r.stdout.splitlines()
    assert "VALIDO" in saida
    assert "URL=sqlite:////var/lib/api-tarefas/tarefas.db" in saida
    assert "NOME=CyberIncident API" in saida
    assert saida[-1] == "1"  # sem duplicatas de DATABASE_URL
    # A linha de exemplo comentada para producao nao pode ser alterada.
    assert "# DATABASE_URL=sqlite:////var/lib/api-tarefas/tarefas.db" in bash(
        'env_set "$ENVF" DATABASE_URL "$DB_URL"; cat "$ENVF"', exemplo
    ).stdout


def test_valores_lidos_chegam_ao_config_py(monkeypatch):
    """O mesmo valor que o install.sh le deve ser o que app/config.py recebe."""
    import importlib

    exemplo = (RAIZ / ".env.example").read_text(encoding="utf-8")
    r = bash(
        'env_set "$ENVF" DATABASE_URL "$DB_URL"\n'
        'for k in "${CONFIG_KEYS[@]}"; do printf "%s\\0" "$k=$(env_get "$ENVF" "$k")"; done',
        exemplo,
    )
    assert r.returncode == 0, r.stderr
    for par in filter(None, r.stdout.split("\0")):
        chave, _, valor = par.partition("=")
        monkeypatch.setenv(chave, valor)
    import app.config as config

    novo = importlib.reload(config).settings
    try:
        assert novo.APP_NAME == "CyberIncident API"
        assert novo.DATABASE_URL == "sqlite:////var/lib/api-tarefas/tarefas.db"
        assert novo.MAX_PAGE_SIZE == 100
        assert novo.SEED_DEMO_DATA is False
    finally:
        monkeypatch.undo()
        importlib.reload(config)


@pytest.mark.parametrize(
    "linha",
    [
        "DATABASE_URL=sqlite:///./data/tarefas.db",      # relativo
        "DATABASE_URL=sqlite:////tmp/outro/tarefas.db",   # fora de DATA_DIR
        "DATABASE_URL=sqlite:////var/lib/api-tarefas/../x.db",
        "DATABASE_URL=postgresql://u:senha@h/db",         # nao SQLite
        "MAX_PAGE_SIZE=abc",
        "MAX_PAGE_SIZE=0",
        "TITULO_MAX_LENGTH=-5",
    ],
)
def test_validacao_rejeita_configuracoes_que_quebrariam_o_servico(linha):
    texto = "DATABASE_URL=sqlite:////var/lib/api-tarefas/tarefas.db\n" + linha + "\n"
    r = bash('validate_env_file "$ENVF"', texto)
    assert r.returncode == 1
    assert "ERRO" in r.stderr
    assert "senha" not in r.stderr  # nunca vaza valores


def test_validacao_exige_database_url_e_avisa_sobre_export():
    assert bash('validate_env_file "$ENVF"', "APP_NAME=x\n").returncode == 1
    r = bash(
        'validate_env_file "$ENVF"',
        "export APP_NAME=x\nDATABASE_URL=sqlite:////var/lib/api-tarefas/tarefas.db\n",
    )
    assert r.returncode == 0
    assert "linha ignorada pelo systemd" in r.stderr


def test_env_set_preserva_valores_com_caracteres_especiais():
    r = bash(
        r'env_set "$ENVF" SEGREDO "a b&c#d\e|f/g" && env_get "$ENVF" SEGREDO',
        "OUTRA=1\n",
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout == r"a b&c#d\e|f/g"
