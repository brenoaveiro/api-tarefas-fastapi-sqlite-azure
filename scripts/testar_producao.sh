#!/usr/bin/env bash
#
# testar_producao.sh — Bateria automatica de testes da CyberIncident API publicada na Azure.
#
# Uso:  ./scripts/testar_producao.sh <IP-PUBLICO> <chave-ssh> [usuario]
# Requer: curl, python3 e acesso SSH a VM. Deve rodar de um IP liberado para escrita no
# Nginx (docs/GUIA_AZURE.md). Usa dados ficticios e remove apenas o incidente que criou.
#
set -u
IP="${1:?uso: $0 <IP> <chave-ssh> [usuario]}"
KEY="${2:?uso: $0 <IP> <chave-ssh> [usuario]}"
USR="${3:-azureuser}"
BASE="http://${IP}"
PASS=0; FAIL=0
PY="$(command -v python3 || command -v python)"

json() { "$PY" -c "import sys,json; d=json.load(sys.stdin); print($1)" 2>/dev/null; }
check() { # descricao esperado obtido
  if [[ "$2" == "$3" ]]; then PASS=$((PASS+1)); echo "[OK]    $1 -> esperado $2, obtido $3"
  else FAIL=$((FAIL+1)); echo "[FALHA] $1 -> esperado $2, obtido $3"; fi
}
code() { curl -s -m 15 -o /dev/null -w '%{http_code}' "$@"; }
H=(-H 'Content-Type: application/json')
ssh_vm() { ssh -i "$KEY" -o ConnectTimeout=20 "${USR}@${IP}" "$@"; }

echo "Teste de producao da CyberIncident API em ${BASE} - $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "------------------------------------------------------------"

echo "--- Disponibilidade e interface"
check "GET /health" 200 "$(code "$BASE/health")"
echo "        corpo: $(curl -s -m 15 "$BASE/health")"
check "GET / (dashboard)" 200 "$(code "$BASE/")"
check "dashboard contem o nome da aplicacao" 1 "$(curl -s "$BASE/" | grep -c 'CyberIncident API' | sed 's/^[1-9][0-9]*$/1/')"
check "GET /static/dashboard.js" 200 "$(code "$BASE/static/dashboard.js")"
check "GET /docs (Swagger personalizado)" 200 "$(code "$BASE/docs")"
check "Swagger usa assets locais (sem CDN)" 0 "$(curl -s "$BASE/docs" | grep -c 'cdn.jsdelivr.net')"
check "GET /openapi.json" 200 "$(code "$BASE/openapi.json")"

echo "--- Estatisticas coerentes com a listagem"
TOTAL_LISTA="$(curl -s "$BASE/incidentes?limit=1" | json "d['total']")"
TOTAL_STATS="$(curl -s "$BASE/incidentes/estatisticas" | json "d['total']")"
check "estatisticas.total == listagem.total" "$TOTAL_LISTA" "$TOTAL_STATS"
check "soma por_severidade == total" "$TOTAL_STATS" "$(curl -s "$BASE/incidentes/estatisticas" | json "sum(d['por_severidade'].values())")"
ANTES="$TOTAL_STATS"

echo "--- CRUD (incidente ficticio de teste)"
RESP="$(curl -s -m 15 -w '\n%{http_code}' -X POST "$BASE/incidentes" "${H[@]}" \
  -d '{"titulo":"[TESTE] Incidente ficticio de validacao","descricao":"Criado pelo script de teste (dados ficticios).","categoria":"anomalia_rede","severidade":"media","ip_origem":"198.51.100.7","ativo_afetado":"srv-teste-01"}')"
check "POST /incidentes" 201 "$(echo "$RESP" | tail -1)"
ID="$(echo "$RESP" | head -n -1 | json "d['id']")"
echo "        id criado: ${ID}"
check "status inicial = aberto" aberto "$(echo "$RESP" | head -n -1 | json "d['status']")"
check "GET /incidentes" 200 "$(code "$BASE/incidentes")"
check "GET /incidentes?severidade=media" 200 "$(code "$BASE/incidentes?severidade=media")"
check "GET /incidentes/{id}" 200 "$(code "$BASE/incidentes/${ID}")"
check "PUT /incidentes/{id}" 200 "$(code -X PUT "$BASE/incidentes/${ID}" "${H[@]}" -d '{"titulo":"[TESTE] atualizado","descricao":"Atualizado pelo teste.","categoria":"anomalia_rede","severidade":"alta","ip_origem":"198.51.100.7","ativo_afetado":"srv-teste-01","status":"aberto"}')"
check "PATCH status aberto->em_analise" 200 "$(code -X PATCH "$BASE/incidentes/${ID}/status" "${H[@]}" -d '{"status":"em_analise"}')"
check "PATCH transicao invalida (em_analise->aberto)" 422 "$(code -X PATCH "$BASE/incidentes/${ID}/status" "${H[@]}" -d '{"status":"aberto"}')"
check "PATCH em_analise->resolvido" 200 "$(code -X PATCH "$BASE/incidentes/${ID}/status" "${H[@]}" -d '{"status":"resolvido"}')"
check "resolvido_em preenchido" True "$(curl -s "$BASE/incidentes/${ID}" | json "d['resolvido_em'] is not None")"
check "POST severidade invalida" 422 "$(code -X POST "$BASE/incidentes" "${H[@]}" -d '{"titulo":"abc","descricao":"abcde","categoria":"malware","severidade":"extrema","ativo_afetado":"x"}')"
check "POST ip invalido" 422 "$(code -X POST "$BASE/incidentes" "${H[@]}" -d '{"titulo":"abc","descricao":"abcde","categoria":"malware","severidade":"baixa","ip_origem":"999.9.9.9","ativo_afetado":"x"}')"
check "GET id inexistente" 404 "$(code "$BASE/incidentes/999999")"

echo "--- Persistencia: reiniciando apenas o servico api-tarefas"
ssh_vm 'sudo systemctl restart api-tarefas && sleep 4 && systemctl is-active api-tarefas'
for i in $(seq 1 15); do [[ "$(code "$BASE/health")" == 200 ]] && break; sleep 2; done
check "GET /health apos reinicio" 200 "$(code "$BASE/health")"
check "incidente preservado apos reinicio" resolvido "$(curl -s "$BASE/incidentes/${ID}" | json "d['status']")"

check "DELETE /incidentes/{id}" 204 "$(code -X DELETE "$BASE/incidentes/${ID}")"
check "GET apos DELETE" 404 "$(code "$BASE/incidentes/${ID}")"
check "total voltou ao valor inicial" "$ANTES" "$(curl -s "$BASE/incidentes/estatisticas" | json "d['total']")"

echo "--- Seguranca"
check "porta 8000 NAO exposta" 000 "$(curl -s -m 6 -o /dev/null -w '%{http_code}' "http://${IP}:8000/health" || true)"
W="$(ssh_vm "for m in POST PUT PATCH DELETE; do curl -s -m 8 -o /dev/null -w \"\$m=%{http_code} \" -X \$m -H 'Content-Type: application/json' -d '{}' http://${IP}/incidentes/1; done")"
echo "        escrita a partir de IP NAO autorizado (a propria VM): ${W}"
check "escrita de IP nao autorizado bloqueada (403 x4)" "POST=403 PUT=403 PATCH=403 DELETE=403 " "${W}"
echo "--- Banco SQLite na VM"
ssh_vm 'sudo ls -l /var/lib/api-tarefas/tarefas.db; sudo sqlite3 -readonly /var/lib/api-tarefas/tarefas.db "PRAGMA journal_mode; PRAGMA integrity_check; .tables"'
check "tabela antiga tarefas preservada" 1 "$(ssh_vm 'sudo sqlite3 -readonly /var/lib/api-tarefas/tarefas.db "SELECT count(*) FROM tarefas;"')"

echo "------------------------------------------------------------"
echo "Resumo: ${PASS} aprovados, ${FAIL} falhas"
[[ "$FAIL" -eq 0 ]]
