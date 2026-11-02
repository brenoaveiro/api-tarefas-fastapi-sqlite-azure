#!/usr/bin/env bash
#
# testar_producao.sh — Bateria automatica de testes contra a API publicada na Azure.
#
# Uso:  ./scripts/testar_producao.sh <IP-PUBLICO> <chave-ssh> [usuario]
# Requer: curl, python3 (para ler JSON) e acesso SSH a VM (para provar a
# persistencia reiniciando o servico). Roda a partir de um IP liberado para
# escrita no Nginx (ver docs/GUIA_AZURE.md). Usa apenas dados ficticios e apaga
# ao final somente o registro que ele mesmo criou.
#
set -u
IP="${1:?uso: $0 <IP> <chave-ssh> [usuario]}"
KEY="${2:?uso: $0 <IP> <chave-ssh> [usuario]}"
USR="${3:-azureuser}"
BASE="http://${IP}"
PASS=0; FAIL=0

json() { python3 -c "import sys,json; d=json.load(sys.stdin); print($1)" 2>/dev/null || python -c "import sys,json; d=json.load(sys.stdin); print($1)"; }
check() { # descricao esperado obtido
  if [[ "$2" == "$3" ]]; then PASS=$((PASS+1)); echo "[OK]    $1 -> esperado $2, obtido $3"
  else FAIL=$((FAIL+1)); echo "[FALHA] $1 -> esperado $2, obtido $3"; fi
}
code() { curl -s -m 15 -o /dev/null -w '%{http_code}' "$@"; }

echo "Teste de producao em ${BASE} - $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "------------------------------------------------------------"

check "GET /health" 200 "$(code "$BASE/health")"
echo "        corpo: $(curl -s -m 15 "$BASE/health")"
check "GET /docs (Swagger UI)" 200 "$(code "$BASE/docs")"
check "GET /openapi.json" 200 "$(code "$BASE/openapi.json")"

ANTES="$(curl -s -m 15 "$BASE/tarefas" | json "d['total']")"
echo "        tarefas antes do teste: ${ANTES}"

RESP="$(curl -s -m 15 -w '\n%{http_code}' -X POST "$BASE/tarefas" -H 'Content-Type: application/json' \
  -d '{"titulo":"[TESTE] tarefa ficticia de validacao","descricao":"criada pelo script de teste"}')"
check "POST /tarefas" 201 "$(echo "$RESP" | tail -1)"
ID="$(echo "$RESP" | head -n -1 | json "d['id']")"
echo "        id criado: ${ID}"

check "GET /tarefas" 200 "$(code "$BASE/tarefas")"
check "GET /tarefas/{id}" 200 "$(code "$BASE/tarefas/${ID}")"
check "PUT /tarefas/{id}" 200 "$(code -X PUT "$BASE/tarefas/${ID}" -H 'Content-Type: application/json' -d '{"titulo":"[TESTE] atualizada","concluida":true}')"
check "valor atualizado persistido (concluida)" True "$(curl -s -m 15 "$BASE/tarefas/${ID}" | json "d['concluida']")"
check "POST invalido (titulo vazio)" 422 "$(code -X POST "$BASE/tarefas" -H 'Content-Type: application/json' -d '{"titulo":""}')"
check "GET id inexistente (404)" 404 "$(code "$BASE/tarefas/999999")"

echo "--- Persistencia: reiniciando o servico api-tarefas na VM"
ssh -i "$KEY" -o ConnectTimeout=20 "${USR}@${IP}" 'sudo systemctl restart api-tarefas && sleep 4 && systemctl is-active api-tarefas'
for i in $(seq 1 15); do [[ "$(code "$BASE/health")" == 200 ]] && break; sleep 2; done
check "GET /health apos reinicio" 200 "$(code "$BASE/health")"
check "registro continua apos reinicio (GET /tarefas/{id})" 200 "$(code "$BASE/tarefas/${ID}")"
check "titulo preservado apos reinicio" "[TESTE] atualizada" "$(curl -s -m 15 "$BASE/tarefas/${ID}" | json "d['titulo']")"

check "DELETE /tarefas/{id}" 204 "$(code -X DELETE "$BASE/tarefas/${ID}")"
check "GET apos DELETE (404)" 404 "$(code "$BASE/tarefas/${ID}")"
DEPOIS="$(curl -s -m 15 "$BASE/tarefas" | json "d['total']")"
check "total de tarefas voltou ao valor inicial" "$ANTES" "$DEPOIS"

echo "--- Seguranca"
check "porta 8000 NAO exposta (sem resposta)" 000 "$(curl -s -m 6 -o /dev/null -w '%{http_code}' "http://${IP}:8000/health" || true)"
echo "--- Banco SQLite na VM"
ssh -i "$KEY" -o ConnectTimeout=20 "${USR}@${IP}" 'sudo ls -l /var/lib/api-tarefas/; sudo sqlite3 /var/lib/api-tarefas/tarefas.db "PRAGMA journal_mode; PRAGMA integrity_check; SELECT count(*) AS tarefas FROM tarefas;"'

echo "------------------------------------------------------------"
echo "Resumo: ${PASS} aprovados, ${FAIL} falhas"
[[ "$FAIL" -eq 0 ]]
