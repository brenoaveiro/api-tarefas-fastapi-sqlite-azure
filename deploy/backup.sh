#!/usr/bin/env bash
#
# backup.sh — Realiza um backup CONSISTENTE do banco SQLite em produção,
# mesmo com a aplicacao em execucao.
#
# Nao copia o arquivo .db diretamente (uma copia "cp" de um arquivo
# SQLite em uso pode ficar corrompida ou inconsistente, especialmente
# em modo WAL). Em vez disso, usa o comando ".backup" do sqlite3, que
# realiza uma copia atomica e segura por meio da API oficial de backup
# do SQLite.
#
# Uso (na VM):
#   sudo ./deploy/backup.sh
#
set -euo pipefail

DATA_DIR="/var/lib/api-tarefas"
DB_FILE="$DATA_DIR/tarefas.db"
BACKUP_DIR="$DATA_DIR/backups"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_FILE="$BACKUP_DIR/tarefas_${TIMESTAMP}.db"

if [[ ! -f "$DB_FILE" ]]; then
  echo "ERRO: banco de dados nao encontrado em ${DB_FILE}."
  exit 1
fi

mkdir -p "$BACKUP_DIR"

echo "==> Gerando backup consistente de ${DB_FILE}"
sqlite3 "$DB_FILE" ".backup '${BACKUP_FILE}'"

echo "==> Verificando integridade do backup"
INTEGRIDADE=$(sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;")
if [[ "$INTEGRIDADE" != "ok" ]]; then
  echo "ERRO: verificacao de integridade falhou: ${INTEGRIDADE}"
  exit 1
fi

echo "==> Backup concluido com sucesso: ${BACKUP_FILE}"

# Mantem apenas os 14 backups mais recentes, para nao esgotar o disco
# da VM (que e pequeno na SKU Standard_B2ats_v2).
cd "$BACKUP_DIR"
ls -1t tarefas_*.db 2>/dev/null | tail -n +15 | xargs -r rm -f --
echo "==> Backups antigos (alem dos 14 mais recentes) removidos, se existentes."

cat <<EOF

Para restaurar este backup (interrompendo a aplicacao antes):
  sudo systemctl stop api-tarefas
  sudo cp "${BACKUP_FILE}" "${DB_FILE}"
  sudo chown apitarefas:apitarefas "${DB_FILE}"
  sudo systemctl start api-tarefas
  curl http://127.0.0.1:8000/health
EOF
