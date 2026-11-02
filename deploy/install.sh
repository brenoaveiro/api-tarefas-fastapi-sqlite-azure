#!/usr/bin/env bash
#
# install.sh — Instalacao inicial da API de Tarefas em uma VM Ubuntu
# (Azure, SKU Standard_B1s ou equivalente).
#
# Este script e idempotente: pode ser executado novamente sem destruir
# configuracoes existentes. Ele NAO sobrescreve um .env ja presente.
#
# Uso (como usuario com sudo, ex.: azureuser):
#   chmod +x deploy/install.sh
#   sudo ./deploy/install.sh https://github.com/<seu-usuario>/api-tarefas-fastapi-sqlite-azure.git
#
# Pre-requisitos:
#   - VM Ubuntu Server LTS provisionada na Azure.
#   - Acesso SSH funcionando.
#   - Porta 22 liberada apenas para o IP do administrador (NSG).
#
set -euo pipefail

REPO_URL="${1:-}"
APP_DIR="/opt/api-tarefas"
DATA_DIR="/var/lib/api-tarefas"
SERVICE_USER="apitarefas"

if [[ -z "$REPO_URL" ]]; then
  echo "Uso: sudo ./install.sh <url-do-repositorio-git>"
  exit 1
fi

if [[ "$EUID" -ne 0 ]]; then
  echo "Este script precisa ser executado com sudo/root."
  exit 1
fi

echo "==> 1/12: Atualizando pacotes do sistema"
apt-get update -y
apt-get upgrade -y

echo "==> 2/12: Instalando dependencias do sistema (Python, Nginx, Git, sqlite3)"
apt-get install -y python3 python3-venv python3-pip nginx git sqlite3

echo "==> 3/12: Criando usuario de servico sem privilegios (${SERVICE_USER})"
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
else
  echo "    Usuario ${SERVICE_USER} ja existe, mantendo."
fi

echo "==> 4/12: Criando diretorio da aplicacao e diretorio persistente de dados"
mkdir -p "$APP_DIR"
mkdir -p "$DATA_DIR"
chown -R "$SERVICE_USER":"$SERVICE_USER" "$DATA_DIR"
chmod 750 "$DATA_DIR"

echo "==> 5/12: Clonando ou atualizando o repositorio"
if [[ -d "$APP_DIR/.git" ]]; then
  echo "    Repositorio ja existe em ${APP_DIR}, atualizando (git pull)..."
  git -C "$APP_DIR" pull --ff-only
else
  git clone "$REPO_URL" "$APP_DIR"
fi

echo "==> 6/12: Criando ambiente virtual Python"
if [[ ! -d "$APP_DIR/.venv" ]]; then
  python3 -m venv "$APP_DIR/.venv"
fi

echo "==> 7/12: Instalando dependencias Python"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "==> 8/12: Configurando variaveis de ambiente (.env)"
if [[ ! -f "$APP_DIR/.env" ]]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  sed -i "s#^DATABASE_URL=.*#DATABASE_URL=sqlite:////${DATA_DIR#/}/tarefas.db#" "$APP_DIR/.env"
  echo "    Arquivo .env criado a partir de .env.example. Revise se necessario."
else
  echo "    Arquivo .env ja existe, mantendo configuracao atual."
fi

echo "==> 9/12: Ajustando permissoes do diretorio da aplicacao"
chown -R "$SERVICE_USER":"$SERVICE_USER" "$APP_DIR"

echo "==> 10/12: Inicializando o banco de dados (criacao das tabelas)"
sudo -u "$SERVICE_USER" bash -c "cd '$APP_DIR' && set -a && source .env && set +a && '$APP_DIR/.venv/bin/python' -c 'from app.database import Base, engine; import app.models; Base.metadata.create_all(bind=engine)'"

echo "==> 11/12: Configurando o servico systemd"
cp "$APP_DIR/deploy/systemd/api-tarefas.service" /etc/systemd/system/api-tarefas.service
systemctl daemon-reload
systemctl enable api-tarefas
systemctl restart api-tarefas

echo "==> 12/12: Configurando o Nginx"
cp "$APP_DIR/deploy/nginx/api-tarefas.conf" /etc/nginx/sites-available/api-tarefas.conf
ln -sf /etc/nginx/sites-available/api-tarefas.conf /etc/nginx/sites-enabled/api-tarefas.conf
# Remove o site padrao do Nginx, se ainda estiver habilitado, para evitar conflito.
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo ""
echo "===================================================================="
echo " Instalacao concluida. Verificando saude da aplicacao localmente..."
echo "===================================================================="
sleep 2
curl -sf http://127.0.0.1:8000/health && echo "" || echo "ATENCAO: health check local falhou. Verifique: systemctl status api-tarefas"
echo ""
echo "Teste externo (substitua pelo IP publico da VM):"
echo "  curl http://<IP-PUBLICO-DA-VM>/health"
