#!/usr/bin/env bash
#
# testar_producao.sh — Bateria de verificacoes da CyberIncident API publicada na Azure.
#
# Uso:  ./scripts/testar_producao.sh <IP-PUBLICO> <chave-ssh> [usuario]
# Variaveis opcionais:
#   REQUIRE_HTTPS=1   exige HTTPS valido (sem isso, HTTPS nao configurado vira "N/A", nao falha)
#
# Requisitos: curl, openssl, python3 e acesso SSH a VM. Rode de um IP liberado para escrita no Nginx.
# Dados ficticios; remove apenas o incidente que o proprio teste criou (mesmo se o teste for interrompido).
#
# Contagem: cada verificacao conta UMA vez como aprovada ([OK]) ou falha ([FALHA]). Erros de SSH,
# de SQLite e de leitura de JSON tambem sao falhas contabilizadas. O codigo de saida e 0 somente
# se nao houve nenhuma falha.
#
set -u
IP="${1:?uso: $0 <IP> <chave-ssh> [usuario]}"
KEY="${2:?uso: $0 <IP> <chave-ssh> [usuario]}"
USR="${3:-azureuser}"
BASE="http://${IP}"
SBASE="https://${IP}"
DB="/var/lib/api-tarefas/tarefas.db"
PASS=0; FAIL=0; NA=0
ID=""                                   # incidente criado por este teste
PY="$(command -v python3 || command -v python)"
H=(-H 'Content-Type: application/json')

limpar() {                              # remove somente o registro criado por este script
  if [[ -n "$ID" ]]; then
    curl -s -o /dev/null -m 10 -X DELETE "${BASE}/incidentes/${ID}" || true
  fi
}
trap limpar EXIT

ok()  { PASS=$((PASS+1)); echo "[OK]    $1"; }
bad() { FAIL=$((FAIL+1)); echo "[FALHA] $1"; }
na()  { NA=$((NA+1));     echo "[N/A]   $1"; }
check() {                               # descricao esperado obtido
  if [[ "$2" == "$3" ]]; then ok "$1 -> $3"; else bad "$1 -> esperado '$2', obtido '$3'"; fi
}
code() { curl -s -m 15 -o /dev/null -w '%{http_code}' "$@" || true; }
json() { "$PY" -c "import sys,json; d=json.load(sys.stdin); print($1)" 2>/dev/null || echo "ERRO_JSON"; }
ssh_vm() {                              # preenche SSH_OUT e SSH_RC
  SSH_OUT="$(ssh -i "$KEY" -o ConnectTimeout=20 -o BatchMode=yes "${USR}@${IP}" "$1" 2>&1)"; SSH_RC=$?
}
check_ssh() {                           # descricao esperado comando-remoto
  ssh_vm "$3"
  if [[ $SSH_RC -ne 0 ]]; then bad "$1 -> comando SSH falhou (codigo ${SSH_RC}): ${SSH_OUT}"
  else check "$1" "$2" "$(echo "$SSH_OUT" | tr -d '\r' | sed -e 's/[[:space:]]*$//')"; fi
}

echo "CyberIncident API - verificacoes de producao em ${BASE} - $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "------------------------------------------------------------"

echo "--- Disponibilidade e interface"
check "GET /health" 200 "$(code "$BASE/health")"
check "corpo do /health" "ok|ok" "$(curl -s -m 15 "$BASE/health" | json "d['status']+'|'+d['database']")"
check "GET / (dashboard)" 200 "$(code "$BASE/")"
check "dashboard contem 'CyberIncident API'" sim "$(curl -s -m 15 "$BASE/" | grep -q 'CyberIncident API' && echo sim || echo nao)"
check "GET /static/dashboard.js" 200 "$(code "$BASE/static/dashboard.js")"
check "GET /static/dashboard.css" 200 "$(code "$BASE/static/dashboard.css")"
check "GET /docs (Swagger personalizado)" 200 "$(code "$BASE/docs")"
check "Swagger sem CDN externo" nao "$(curl -s -m 15 "$BASE/docs" | grep -q 'cdn.jsdelivr.net' && echo sim || echo nao)"
check "GET /static/swagger/swagger-ui-bundle.js" 200 "$(code "$BASE/static/swagger/swagger-ui-bundle.js")"
check "GET /static/swagger/swagger-ui.css" 200 "$(code "$BASE/static/swagger/swagger-ui.css")"
check "GET /openapi.json" 200 "$(code "$BASE/openapi.json")"

echo "--- Estatisticas coerentes com a listagem"
TOTAL_LISTA="$(curl -s -m 15 "$BASE/incidentes?limit=1" | json "d['total']")"
TOTAL_STATS="$(curl -s -m 15 "$BASE/incidentes/estatisticas" | json "d['total']")"
check "estatisticas.total == listagem.total" "$TOTAL_LISTA" "$TOTAL_STATS"
check "soma por_severidade == total" "$TOTAL_STATS" "$(curl -s -m 15 "$BASE/incidentes/estatisticas" | json "sum(d['por_severidade'].values())")"
check "soma por_status == total" "$TOTAL_STATS" "$(curl -s -m 15 "$BASE/incidentes/estatisticas" | json "sum(d['por_status'].values())")"
check "soma por_categoria == total" "$TOTAL_STATS" "$(curl -s -m 15 "$BASE/incidentes/estatisticas" | json "sum(d['por_categoria'].values())")"
ANTES="$TOTAL_STATS"

echo "--- CRUD (incidente ficticio de teste)"
RESP="$(curl -s -m 15 -w '\n%{http_code}' -X POST "$BASE/incidentes" "${H[@]}" \
  -d '{"titulo":"[TESTE] Incidente ficticio de validacao","descricao":"Criado pelo script de teste (dados ficticios).","categoria":"anomalia_rede","severidade":"media","ip_origem":"198.51.100.7","ativo_afetado":"srv-teste-01"}')"
CODIGO_POST="$(echo "$RESP" | tail -n 1)"
check "POST /incidentes" 201 "$CODIGO_POST"
if [[ "$CODIGO_POST" == "201" ]]; then
  ID="$(echo "$RESP" | head -n -1 | json "d['id']")"
  [[ "$ID" =~ ^[0-9]+$ ]] || { bad "id do incidente criado ilegivel ('${ID}')"; ID=""; }
fi
if [[ -z "$ID" ]]; then
  bad "CRUD dependente do POST nao executado (nenhum incidente criado)"
else
  echo "        id criado: ${ID}"
  check "status inicial = aberto" aberto "$(curl -s -m 15 "$BASE/incidentes/${ID}" | json "d['status']")"
  check "GET /incidentes" 200 "$(code "$BASE/incidentes")"
  check "GET /incidentes?severidade=media" 200 "$(code "$BASE/incidentes?severidade=media")"
  check "GET /incidentes/{id}" 200 "$(code "$BASE/incidentes/${ID}")"
  check "PUT /incidentes/{id}" 200 "$(code -X PUT "$BASE/incidentes/${ID}" "${H[@]}" -d '{"titulo":"[TESTE] atualizado","descricao":"Atualizado pelo teste.","categoria":"anomalia_rede","severidade":"alta","ip_origem":"198.51.100.7","ativo_afetado":"srv-teste-01","status":"aberto"}')"
  check "PUT alterou a severidade" alta "$(curl -s -m 15 "$BASE/incidentes/${ID}" | json "d['severidade']")"
  check "PATCH status aberto->em_analise" 200 "$(code -X PATCH "$BASE/incidentes/${ID}/status" "${H[@]}" -d '{"status":"em_analise"}')"
  check "PATCH transicao invalida (em_analise->aberto)" 422 "$(code -X PATCH "$BASE/incidentes/${ID}/status" "${H[@]}" -d '{"status":"aberto"}')"
  check "PATCH em_analise->resolvido" 200 "$(code -X PATCH "$BASE/incidentes/${ID}/status" "${H[@]}" -d '{"status":"resolvido"}')"
  check "resolvido_em preenchido" True "$(curl -s -m 15 "$BASE/incidentes/${ID}" | json "d['resolvido_em'] is not None")"
  check "PATCH reabertura resolvido->aberto" 200 "$(code -X PATCH "$BASE/incidentes/${ID}/status" "${H[@]}" -d '{"status":"aberto"}')"
  check "resolvido_em limpo ao reabrir" True "$(curl -s -m 15 "$BASE/incidentes/${ID}" | json "d['resolvido_em'] is None")"
  check "PATCH volta a em_analise e resolvido (para o teste de persistencia)" 200 "$(code -X PATCH "$BASE/incidentes/${ID}/status" "${H[@]}" -d '{"status":"em_analise"}')"
  code -X PATCH "$BASE/incidentes/${ID}/status" "${H[@]}" -d '{"status":"resolvido"}' >/dev/null
fi
check "POST severidade invalida" 422 "$(code -X POST "$BASE/incidentes" "${H[@]}" -d '{"titulo":"abc","descricao":"abcde","categoria":"malware","severidade":"extrema","ativo_afetado":"x"}')"
check "POST ip invalido" 422 "$(code -X POST "$BASE/incidentes" "${H[@]}" -d '{"titulo":"abc","descricao":"abcde","categoria":"malware","severidade":"baixa","ip_origem":"999.9.9.9","ativo_afetado":"x"}')"
check "POST sem campo obrigatorio" 422 "$(code -X POST "$BASE/incidentes" "${H[@]}" -d '{"titulo":"abc"}')"
check "GET id inexistente" 404 "$(code "$BASE/incidentes/999999")"

echo "--- Persistencia: reiniciando apenas o servico api-tarefas"
ssh_vm 'sudo systemctl restart api-tarefas && sleep 4 && systemctl is-active api-tarefas'
check "servico ativo apos o reinicio" active "$(echo "$SSH_OUT" | tail -n 1)"
for _ in $(seq 1 15); do [[ "$(code "$BASE/health")" == 200 ]] && break; sleep 2; done
check "GET /health apos reinicio" 200 "$(code "$BASE/health")"
if [[ -n "$ID" ]]; then
  check "incidente preservado apos reinicio (status)" resolvido "$(curl -s -m 15 "$BASE/incidentes/${ID}" | json "d['status']")"
  check "DELETE /incidentes/{id}" 204 "$(code -X DELETE "$BASE/incidentes/${ID}")"
  check "GET apos DELETE" 404 "$(code "$BASE/incidentes/${ID}")"
  ID=""                                 # ja removido: nada a limpar
fi
check "total de incidentes voltou ao valor inicial" "$ANTES" "$(curl -s -m 15 "$BASE/incidentes/estatisticas" | json "d['total']")"

echo "--- Seguranca"
check "porta 8000 NAO exposta" 000 "$(curl -s -m 6 -o /dev/null -w '%{http_code}' "http://${IP}:8000/health" 2>/dev/null || true)"
ssh_vm "for m in POST PUT PATCH DELETE; do printf \"\$m=%s \" \"\$(curl -s -m 8 -o /dev/null -w '%{http_code}' -X \$m -H 'Content-Type: application/json' -d '{}' http://${IP}/incidentes/1)\"; done"
if [[ $SSH_RC -ne 0 ]]; then bad "escrita de IP nao autorizado (HTTP) -> comando SSH falhou: ${SSH_OUT}"
else check "escrita de IP nao autorizado bloqueada em HTTP" "POST=403 PUT=403 PATCH=403 DELETE=403" "$(echo "$SSH_OUT" | sed -e 's/[[:space:]]*$//')"; fi
check_ssh "arquivo do banco com permissao 600 e dono apitarefas" "600 apitarefas" "sudo stat -c '%a %U' ${DB}"
check_ssh "Uvicorn escuta somente em 127.0.0.1:8000" 1 "ss -ltn | grep -c '127.0.0.1:8000'"
check_ssh "nada escuta em 0.0.0.0:8000" 0 "ss -ltn | grep -c '0.0.0.0:8000' || true"

echo "--- HTTPS (certificado Let's Encrypt para o IP)"
if [[ "$(curl -s -m 10 -o /dev/null -w '%{http_code}' "${SBASE}/health" 2>/dev/null)" == "200" ]]; then
  check "GET /health via HTTPS com certificado verificado" "200 0" "$(curl -s -m 15 -o /dev/null -w '%{http_code} %{ssl_verify_result}' "${SBASE}/health")"
  CERT="$(echo | openssl s_client -connect "${IP}:443" -servername "${IP}" 2>/dev/null | openssl x509 -noout -issuer -enddate -ext subjectAltName 2>/dev/null)"
  check "emissor do certificado e o Let's Encrypt" sim "$(echo "$CERT" | grep -q "Let's Encrypt" && echo sim || echo nao)"
  check "IP consta no certificado (SAN)" sim "$(echo "$CERT" | grep -q "IP Address:${IP}" && echo sim || echo nao)"
  FIM="$(echo "$CERT" | sed -n 's/^notAfter=//p')"
  if [[ -n "$FIM" ]] && date -d "$FIM" +%s >/dev/null 2>&1; then
    check "certificado ainda valido (expira em: ${FIM})" sim "$([[ $(date -d "$FIM" +%s) -gt $(date +%s) ]] && echo sim || echo nao)"
  else bad "nao foi possivel ler a data de validade do certificado"; fi
  check "GET /docs via HTTPS" 200 "$(code "${SBASE}/docs")"
  check "GET /incidentes/estatisticas via HTTPS" 200 "$(code "${SBASE}/incidentes/estatisticas")"
  ssh_vm "for m in POST PUT PATCH DELETE; do printf \"\$m=%s \" \"\$(curl -s -m 8 -o /dev/null -w '%{http_code}' -X \$m -H 'Content-Type: application/json' -d '{}' https://${IP}/incidentes/1)\"; done"
  if [[ $SSH_RC -ne 0 ]]; then bad "escrita de IP nao autorizado (HTTPS) -> comando SSH falhou: ${SSH_OUT}"
  else check "escrita de IP nao autorizado bloqueada em HTTPS" "POST=403 PUT=403 PATCH=403 DELETE=403" "$(echo "$SSH_OUT" | sed -e 's/[[:space:]]*$//')"; fi
  check_ssh "timer de renovacao do certificado ativo" active "systemctl is-active certbot-renew.timer"
  check_ssh "hook de renovacao recarrega o Nginx" "renew_hook = systemctl reload nginx" "sudo grep '^renew_hook' /etc/letsencrypt/renewal/${IP}.conf"
elif [[ "${REQUIRE_HTTPS:-0}" == "1" ]]; then
  bad "HTTPS exigido (REQUIRE_HTTPS=1), mas ${SBASE}/health nao respondeu 200 com certificado valido"
else
  na "HTTPS nao configurado neste ambiente (as verificacoes de TLS nao se aplicam)"
fi

echo "--- Banco SQLite na VM (somente leitura)"
check_ssh "tabela 'incidentes' existe em sqlite_master" 1 "sudo sqlite3 -readonly ${DB} \"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='incidentes';\""
check_ssh "tabela antiga 'tarefas' preservada (sqlite_master)" 1 "sudo sqlite3 -readonly ${DB} \"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='tarefas';\""
check_ssh "PRAGMA journal_mode" wal "sudo sqlite3 -readonly ${DB} 'PRAGMA journal_mode;'"
check_ssh "PRAGMA integrity_check" ok "sudo sqlite3 -readonly ${DB} 'PRAGMA integrity_check;'"
check_ssh "nenhum incidente de teste residual" 0 "sudo sqlite3 -readonly ${DB} \"SELECT COUNT(*) FROM incidentes WHERE titulo LIKE '[TESTE]%';\""

echo "------------------------------------------------------------"
echo "Resumo: $((PASS+FAIL)) verificacoes executadas | ${PASS} aprovadas | ${FAIL} falhas | ${NA} nao aplicaveis"
[[ "$FAIL" -eq 0 ]]
