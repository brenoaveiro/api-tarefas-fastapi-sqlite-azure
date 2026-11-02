"""Testes de reprodutibilidade e de configuracao de entrega (arquivos, scripts, Nginx, HTTPS, CI)."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


def ler(rel):
    return (RAIZ / rel).read_text(encoding="utf-8")


# ----------------------------------------------------------- arquivos necessarios
@pytest.mark.parametrize("rel", [
    ".gitignore", ".env.example", "pytest.ini", "requirements.txt", "requirements-dev.txt", "LICENSE",
    "app/static/index.html", "app/static/dashboard.js", "app/static/dashboard.css", "app/static/favicon.svg",
    "app/static/swagger-tema.css", "app/static/swagger-tema.js",
    "app/static/swagger/swagger-ui-bundle.js", "app/static/swagger/swagger-ui.css",
    "app/static/swagger/LICENSE-swagger-ui.txt",
    "deploy/install.sh", "deploy/deploy.sh", "deploy/backup.sh", "deploy/https_ip.sh",
    "deploy/nginx/api-tarefas.conf", "deploy/nginx/api-tarefas-https.conf", "deploy/systemd/api-tarefas.service",
    "scripts/testar_producao.sh", ".github/workflows/ci.yml",
])
def test_arquivo_necessario_existe_e_nao_esta_vazio(rel):
    p = RAIZ / rel
    assert p.is_file() and p.stat().st_size > 0, f"ausente ou vazio: {rel}"


def test_assets_do_swagger_integros_e_com_licenca():
    js = (RAIZ / "app/static/swagger/swagger-ui-bundle.js").read_text(encoding="utf-8", errors="ignore")
    assert "SwaggerUIBundle" in js and "5.17.14" in js and len(js) > 1_000_000
    assert ".swagger-ui" in (RAIZ / "app/static/swagger/swagger-ui.css").read_text(encoding="utf-8", errors="ignore")
    assert "Apache License" in ler("app/static/swagger/LICENSE-swagger-ui.txt")


def test_dependencias_fixadas():
    for rel in ("requirements.txt",):
        for linha in ler(rel).splitlines():
            if linha.strip() and not linha.startswith(("#", "-")):
                assert "==" in linha, f"dependencia sem versao fixa: {linha}"


# ---------------------------------------------------------- script de producao
def test_script_producao_usa_sqlite_master_e_nao_conta_linhas():
    s = ler("scripts/testar_producao.sh")
    assert "sqlite_master" in s and "name='tarefas'" in s and "name='incidentes'" in s
    assert not re.search(r"SELECT\s+count\(\*\)\s+FROM\s+tarefas", s, re.I)
    assert "trap limpar EXIT" in s and "PRAGMA integrity_check" in s
    assert "REQUIRE_HTTPS" in s and s.rstrip().endswith('[[ "$FAIL" -eq 0 ]]')   # codigo de saida reflete falhas


def test_script_producao_nao_mistura_metacomandos_sqlite():
    for linha in ler("scripts/testar_producao.sh").splitlines():
        if "sqlite3" in linha:
            assert ".tables" not in linha and ".schema" not in linha, linha


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash indisponivel")
@pytest.mark.parametrize("rel", ["deploy/install.sh", "deploy/deploy.sh", "deploy/backup.sh", "deploy/https_ip.sh",
                                 "scripts/testar_producao.sh"])
def test_sintaxe_bash(rel):
    r = subprocess.run(["bash", "-n", str(RAIZ / rel)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_deploy_aborta_se_o_backup_falhar_e_valida_nginx():
    s = ler("deploy/deploy.sh")
    assert 'bash "$APP_DIR/deploy/backup.sh" ||' in s and "exit 1" in s
    assert "nginx -t" in s and "pre-deploy" in s


# --------------------------------------------------------------- Nginx e HTTPS
def test_nginx_porta_80_tem_acme_e_nao_forca_redirecionamento():
    c = ler("deploy/nginx/api-tarefas.conf")
    assert "/.well-known/acme-challenge/" in c and "/var/www/letsencrypt" in c
    assert "return 301" not in c and "Strict-Transport-Security" not in c   # sem redirect forcado nem HSTS
    assert "limit_except GET HEAD OPTIONS" in c


def test_nginx_https_preserva_protecao_de_escrita_e_tls_moderno():
    c = ler("deploy/nginx/api-tarefas-https.conf")
    assert "listen 443 ssl" in c and "@@IP@@" in c
    assert "limit_except GET HEAD OPTIONS" in c and "deny all;" in c and "api-tarefas-writers" in c
    assert "TLSv1.2 TLSv1.3" in c and "TLSv1 " not in c.replace("TLSv1.2", "").replace("TLSv1.3", "")
    assert "proxy_pass http://127.0.0.1:8000" in c
    assert "Strict-Transport-Security" not in c


def test_script_https_usa_recursos_corretos_do_certbot_para_ip():
    s = ler("deploy/https_ip.sh")
    for trecho in ("--ip-address", "--preferred-profile shortlived", "--webroot", "certbot>=5.4",
                   "--staging", "--deploy-hook", "certbot-renew.timer", "dry-run"):
        assert trecho in s, trecho
    assert "--nginx" not in s     # o plugin nginx do Certbot nao instala certificados de IP


def test_nginx_nao_expoe_a_porta_8000():
    for rel in ("deploy/nginx/api-tarefas.conf", "deploy/nginx/api-tarefas-https.conf"):
        assert not re.search(r"listen\s+(\[::\]:)?8000", ler(rel))


def test_workflow_de_ci_roda_pytest_sem_credenciais():
    w = ler(".github/workflows/ci.yml")
    assert "pytest" in w and "actions/checkout" in w and "setup-python" in w
    assert "secrets." not in w and "AZURE" not in w.upper().replace("AZURE FOR STUDENTS", "")


def test_gitignore_cobre_segredos_bancos_e_ambientes():
    g = ler(".gitignore")
    for padrao in (".env", "*.db", "*.pem", "*.key", ".venv/", "backups/", "__pycache__/"):
        assert padrao in g


def test_env_example_sem_segredos_reais():
    env = ler(".env.example")
    assert not re.search(r"(password|secret|token|key)\s*=\s*\S+", env, re.I)
