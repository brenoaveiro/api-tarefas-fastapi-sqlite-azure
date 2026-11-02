#!/usr/bin/env bash
#
# deploy.sh — Atualiza o codigo da API ja instalada na VM (via install.sh)
# para a versao mais recente do repositorio Git, e reinicia o servico.
#
# Uso (na VM, como usuario com sudo):
#   sudo ./deploy/deploy.sh
#
set -euo pipefail

APP_DIR="/opt/api-tarefas"
SERVICE_USER="apitarefas"
SERVICE_NAME="api-tarefas"

if [[ "$EUID" -ne 0 ]]; then
  echo "Este script precisa ser executado com sudo/root."
  exit 1
fi

if [[ ! -d "$APP_DIR/.git" ]]; then
  echo "ERRO: ${APP_DIR} nao parece conter o repositorio. Execute install.sh primeiro."
  exit 1
fi

echo "==> 1/5: Fazendo backup do banco antes da atualizacao"
"$APP_DIR/deploy/backup.sh" || echo "AVISO: backup falhou ou script de backup nao encontrado. Prosseguindo com cautela."

echo "==> 2/5: Atualizando o codigo (git pull)"
sudo -u "$SERVICE_USER" git -C "$APP_DIR" pull --ff-only

echo "==> 3/5: Atualizando dependencias Python"
sudo -u "$SERVICE_USER" "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "==> 4/5: Reiniciando o servico"
systemctl restart "$SERVICE_NAME"
sleep 2

echo "==> 5/5: Validando saude da aplicacao"
if curl -sf http://127.0.0.1:8000/health; then
  echo ""
  echo "Deploy concluido com sucesso."
else
  echo ""
  echo "ERRO: health check falhou apos o deploy. Verifique: journalctl -u ${SERVICE_NAME} -n 100 --no-pager"
  exit 1
fi
