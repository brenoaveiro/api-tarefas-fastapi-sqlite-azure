#!/usr/bin/env bash
#
# install.sh — Instalacao inicial da CyberIncident API em uma VM Ubuntu
# (Azure, SKU Standard_B1s ou equivalente).
#
# Este script e idempotente: pode ser executado novamente sem destruir
# configuracoes existentes. Ele NAO sobrescreve um .env ja presente.
#
# Uso (como usuario com sudo, ex.: azureuser):
#   chmod +x deploy/install.sh
#   sudo ./deploy/install.sh https://github.com/<seu-usuario>/api-tarefas-fastapi-sqlite-azure.git
#
# Em reexecucoes o argumento e opcional (o repositorio ja esta em /opt).
#
# Pre-requisitos:
#   - VM Ubuntu Server LTS provisionada na Azure.
#   - Acesso SSH funcionando.
#   - Porta 22 liberada apenas para o IP do administrador (NSG).
#
# Sobre o arquivo .env
# --------------------
# O .env NUNCA e carregado com "source"/"." (isso o executaria como
# script Bash: "APP_NAME=CyberIncident API" tentaria rodar o comando "de").
# Ele e lido como DADO, seguindo as mesmas regras do systemd
# (EnvironmentFile=), que e quem realmente o entrega a aplicacao:
#   - uma atribuicao por linha, no formato CHAVE=valor;
#   - linhas iniciadas por # ou ; sao comentarios (nao ha comentario na
#     mesma linha do valor);
#   - o valor vai ate o fim da linha, entao ESPACOS NAO PRECISAM DE ASPAS;
#     aspas simples ou duplas ao redor do valor inteiro sao removidas;
#   - nao ha expansao de $VARIAVEL nem prefixo "export".
# A aplicacao (app/config.py) apenas le os valores via os.getenv().
#
# Este arquivo pode ser carregado com "source" apenas para testes das
# funcoes (a instalacao so roda quando o script e executado diretamente).
#
set -euo pipefail

APP_DIR="/opt/api-tarefas"
DATA_DIR="/var/lib/api-tarefas"
SERVICE_USER="apitarefas"
SERVICE_NAME="api-tarefas"
ENV_FILE="${APP_DIR}/.env"
DB_FILE="${DATA_DIR}/tarefas.db"
# URL SQLAlchemy de caminho absoluto: "sqlite:///" + "/var/lib/..." = 4 barras.
DB_URL="sqlite:///${DB_FILE}"

# Variaveis lidas por app/config.py (mantenha em sincronia com ele).
CONFIG_KEYS=(APP_NAME APP_VERSION DATABASE_URL SEED_DEMO_DATA MAX_PAGE_SIZE TITULO_MAX_LENGTH DESCRICAO_MAX_LENGTH)
INT_KEYS=(MAX_PAGE_SIZE TITULO_MAX_LENGTH DESCRICAO_MAX_LENGTH)

die()  { echo "ERRO: $*" >&2; exit 1; }
warn() { echo "AVISO: $*" >&2; }

# --------------------------------------------------------------------------
# Leitura segura do .env (sem executar nada)
# --------------------------------------------------------------------------

# env_get ARQUIVO CHAVE — imprime o valor de CHAVE (a ultima atribuicao
# vence, como no systemd). Retorna 1 se a chave nao existir.
env_get() {
  local file="$1" key="$2" line v found=1 result=""
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"                              # tolera CRLF
    line="${line#"${line%%[![:space:]]*}"}"           # remove espacos iniciais
    [[ -z "$line" || "$line" == "#"* || "$line" == ";"* ]] && continue
    [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]] || continue
    [[ "${BASH_REMATCH[1]}" == "$key" ]] || continue
    v="${BASH_REMATCH[2]}"
    v="${v%"${v##*[![:space:]]}"}"                    # remove espacos finais
    v="${v#"${v%%[![:space:]]*}"}"                    # remove espacos iniciais
    if (( ${#v} >= 2 )); then
      case "${v:0:1}${v: -1}" in
        '""'|"''") v="${v:1:${#v}-2}" ;;              # remove aspas externas
      esac
    fi
    result="$v"
    found=0
  done < "$file"
  (( found == 0 )) || return 1
  printf '%s' "$result"
}

# env_set ARQUIVO CHAVE VALOR — define CHAVE=VALOR sem usar sed (o valor
# pode ter qualquer caractere). Troca a primeira ocorrencia, remove
# duplicatas e acrescenta ao final se a chave nao existir. Preserva
# dono e permissoes do arquivo.
env_set() {
  local file="$1" key="$2" value="$3" tmp line replaced=0
  tmp="$(mktemp "${file}.XXXXXX")"
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    if [[ "$line" == "${key}="* ]]; then
      if (( replaced == 0 )); then printf '%s=%s\n' "$key" "$value"; replaced=1; fi
    else
      printf '%s\n' "$line"
    fi
  done < "$file" > "$tmp"
  (( replaced == 1 )) || printf '%s=%s\n' "$key" "$value" >> "$tmp"
  cat "$tmp" > "$file"
  rm -f "$tmp"
}

# validate_env_file ARQUIVO — confere se o .env e utilizavel pelo systemd e
# por app/config.py. Falha cedo, com mensagem clara, em vez de deixar o
# servico entrar em loop de reinicio. Nunca imprime valores (podem ser segredos).
validate_env_file() {
  local file="$1" n=0 line key val url path
  while IFS= read -r line || [[ -n "$line" ]]; do
    n=$((n + 1))
    line="${line%$'\r'}"
    line="${line#"${line%%[![:space:]]*}"}"
    [[ -z "$line" || "$line" == "#"* || "$line" == ";"* ]] && continue
    if [[ ! "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
      warn "${file}:${n}: linha ignorada pelo systemd (use CHAVE=valor, sem 'export' nem espacos antes do '=')."
    elif [[ "$line" == *'\' ]]; then
      warn "${file}:${n}: termina com '\\'; o systemd trata isso como continuacao de linha."
    fi
  done < "$file"

  url="$(env_get "$file" DATABASE_URL)" || die "DATABASE_URL ausente em ${file}."
  case "$url" in
    sqlite:////*) path="${url#sqlite:///}" ;;
    sqlite:*)     die "DATABASE_URL SQLite precisa de caminho ABSOLUTO (4 barras), ex.: ${DB_URL}. Um caminho relativo cairia em ${APP_DIR}, somente leitura para o servico (ProtectSystem=strict)." ;;
    *)            die "Esta instalacao suporta apenas SQLite (DATABASE_URL deve comecar com sqlite:////)." ;;
  esac
  if [[ "$path" != "${DATA_DIR}/"* || "$path" == *".."* || "$path" == *"?"* ]]; then
    die "O banco SQLite deve ficar dentro de ${DATA_DIR} (unico diretorio gravavel pelo servico). Ajuste DATABASE_URL para ${DB_URL}."
  fi

  for key in "${INT_KEYS[@]}"; do
    if val="$(env_get "$file" "$key")"; then
      [[ "$val" =~ ^[0-9]+$ && 10#$val -gt 0 ]] \
        || die "${key} deve ser um inteiro positivo (app/config.py usa int()); encontrado valor invalido."
    fi
  done

  if val="$(env_get "$file" SEED_DEMO_DATA)"; then
    case "${val,,}" in
      1|true|yes|on|0|false|no|off|"") ;;
      *) warn "SEED_DEMO_DATA com valor nao reconhecido sera tratado como 'false' por app/config.py." ;;
    esac
  fi
}

# db_path_from_env ARQUIVO — caminho do arquivo SQLite definido no .env.
db_path_from_env() {
  local url
  url="$(env_get "$1" DATABASE_URL)"
  printf '%s' "${url#sqlite:///}"
}

# --------------------------------------------------------------------------
# Execucao como usuario de servico (sem shell, sem HOME)
# --------------------------------------------------------------------------

# as_service CMD... — roda CMD como SERVICE_USER, a partir de "/" (o diretorio
# atual do root pode ser ilegivel para ele) e com HOME inexistente, para o
# git/pip nao tentarem ler arquivos de /root.
as_service() {
  ( cd / && runuser -u "$SERVICE_USER" -- env HOME=/nonexistent "$@" )
}

# init_database — cria as tabelas (idempotente) com o ambiente do .env.
# Os valores sao passados como argumentos de "env" (nunca via shell).
init_database() {
  local key val
  local -a env_args=()
  for key in "${CONFIG_KEYS[@]}"; do
    if val="$(env_get "$ENV_FILE" "$key")"; then
      env_args+=("${key}=${val}")
    fi
  done
  (
    cd "$APP_DIR"
    umask 077   # banco criado como 600 (so o usuario de servico)
    runuser -u "$SERVICE_USER" -- env -i PATH=/usr/bin:/bin HOME=/nonexistent \
      "${env_args[@]}" \
      "$APP_DIR/.venv/bin/python" -c \
      'from app.database import Base, engine; import app.models; Base.metadata.create_all(bind=engine)'
  )
}

# verify_database CAMINHO — confere modo WAL, integridade e a tabela.
verify_database() {
  local db="$1" mode integrity tables
  [[ -f "$db" ]] || die "Banco nao encontrado em ${db} apos a inicializacao."
  mode="$(as_service sqlite3 "$db" 'PRAGMA journal_mode;')"
  [[ "$mode" == "wal" ]] || die "SQLite deveria estar em modo WAL, mas esta em '${mode}'."
  integrity="$(as_service sqlite3 "$db" 'PRAGMA integrity_check;')"
  [[ "$integrity" == "ok" ]] || die "integrity_check do SQLite falhou: ${integrity}"
  tables="$(as_service sqlite3 "$db" ".tables")"
  [[ " ${tables} " == *[[:space:]]incidentes[[:space:]]* ]] || die "Tabela 'incidentes' nao encontrada em ${db}."
  echo "    Banco OK: modo WAL, integridade ok, tabela 'incidentes' presente."
}

# check_mode ALVO DONO:GRUPO MODO — auditoria de permissao.
check_mode() {
  local target="$1" owner="$2" mode="$3" actual
  actual="$(stat -c '%U:%G %a' "$target")"
  [[ "$actual" == "${owner} ${mode}" ]] \
    || die "Permissao inesperada em ${target}: ${actual} (esperado ${owner} ${mode})."
}

wait_for_health() {
  local url="$1" i
  for i in $(seq 1 30); do
    if curl -fsS --max-time 3 "$url" >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  return 1
}

# --------------------------------------------------------------------------
# Instalacao
# --------------------------------------------------------------------------

main() {
  local repo_url="${1:-}" db_path current_url

  set -o errtrace   # faz o trap ERR valer tambem dentro das funcoes
  trap 'echo "ERRO: falha na linha ${LINENO} (comando: ${BASH_COMMAND})" >&2' ERR

  if [[ "$EUID" -ne 0 ]]; then
    echo "Este script precisa ser executado com sudo/root."
    exit 1
  fi
  command -v apt-get >/dev/null || die "Este script suporta apenas Ubuntu/Debian (apt-get)."
  if [[ -z "$repo_url" && ! -d "$APP_DIR/.git" ]]; then
    echo "Uso: sudo ./install.sh <url-do-repositorio-git>"
    exit 1
  fi

  export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a
  local -a apt_opts=(-y -o Dpkg::Options::=--force-confold)

  echo "==> 1/12: Atualizando pacotes do sistema"
  apt-get update -y
  apt-get upgrade "${apt_opts[@]}"

  echo "==> 2/12: Instalando dependencias do sistema (Python, Nginx, Git, sqlite3, curl)"
  apt-get install "${apt_opts[@]}" python3 python3-venv python3-pip nginx git sqlite3 curl

  echo "==> 3/12: Criando usuario de servico sem privilegios (${SERVICE_USER})"
  if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
    useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
  else
    echo "    Usuario ${SERVICE_USER} ja existe, mantendo."
  fi

  echo "==> 4/12: Criando diretorio da aplicacao e diretorio persistente de dados"
  install -d -m 755 "$APP_DIR"
  install -d -m 750 -o "$SERVICE_USER" -g "$SERVICE_USER" "$DATA_DIR"
  # git e pip rodam como o usuario de servico (nunca como root dentro do
  # repositorio): evita "dubious ownership" e arquivos de root na arvore.
  # O .env fica de fora: pertence ao root (ver passo 8).
  find "$APP_DIR" -xdev -path "$ENV_FILE" -prune -o -exec chown -h "$SERVICE_USER:$SERVICE_USER" {} +
  # Reaplica dono/modo do diretorio de dados (corrige backups criados por root).
  chown -R "$SERVICE_USER:$SERVICE_USER" "$DATA_DIR"
  chmod 750 "$DATA_DIR"

  echo "==> 5/12: Clonando ou atualizando o repositorio"
  if [[ -d "$APP_DIR/.git" ]]; then
    echo "    Repositorio ja existe em ${APP_DIR}, atualizando (git pull)..."
    if [[ -n "$repo_url" ]]; then
      current_url="$(as_service git -C "$APP_DIR" remote get-url origin 2>/dev/null || true)"
      [[ "$current_url" == "$repo_url" ]] \
        || warn "origin atual (${current_url:-desconhecido}) difere da URL informada; mantendo o origin atual."
    fi
    as_service git -C "$APP_DIR" pull --ff-only
  else
    if [[ -n "$(ls -A "$APP_DIR")" ]]; then
      die "${APP_DIR} nao esta vazio e nao e um repositorio git. Mova ou remova o conteudo e tente de novo."
    fi
    as_service git clone "$repo_url" "$APP_DIR"
  fi

  echo "==> 6/12: Criando ambiente virtual Python"
  if [[ ! -x "$APP_DIR/.venv/bin/python" ]]; then
    rm -rf "$APP_DIR/.venv"   # venv incompleto de uma execucao interrompida
    as_service python3 -m venv "$APP_DIR/.venv"
  else
    echo "    Ambiente virtual ja existe, mantendo."
  fi

  echo "==> 7/12: Instalando dependencias Python"
  as_service "$APP_DIR/.venv/bin/pip" install --no-cache-dir --upgrade pip
  as_service "$APP_DIR/.venv/bin/pip" install --no-cache-dir -r "$APP_DIR/requirements.txt"

  echo "==> 8/12: Configurando variaveis de ambiente (.env)"
  if [[ ! -f "$ENV_FILE" ]]; then
    [[ -f "$APP_DIR/.env.example" ]] || die "${APP_DIR}/.env.example nao encontrado."
    install -m 600 -o root -g root "$APP_DIR/.env.example" "$ENV_FILE"
    env_set "$ENV_FILE" DATABASE_URL "$DB_URL"
    echo "    Arquivo .env criado a partir de .env.example. Revise se necessario."
  else
    echo "    Arquivo .env ja existe, mantendo configuracao atual."
    # Normaliza CRLF (arquivo editado no Windows): o systemd manteria o \r no valor.
    if grep -q $'\r' "$ENV_FILE"; then
      sed -i 's/\r$//' "$ENV_FILE"
      echo "    CRLF removido do .env."
    fi
    # Sem DATABASE_URL o app usaria /opt/api-tarefas/data (somente leitura).
    if ! env_get "$ENV_FILE" DATABASE_URL >/dev/null; then
      env_set "$ENV_FILE" DATABASE_URL "$DB_URL"
      echo "    DATABASE_URL ausente: definido como ${DB_URL}."
    fi
  fi
  # Segredos: legivel apenas pelo root. O systemd le o EnvironmentFile como
  # root antes de trocar para o usuario de servico, entao 600 e suficiente.
  chown root:root "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  validate_env_file "$ENV_FILE"
  db_path="$(db_path_from_env "$ENV_FILE")"

  echo "==> 9/12: Auditando permissoes"
  check_mode "$ENV_FILE" "root:root" 600
  check_mode "$DATA_DIR" "${SERVICE_USER}:${SERVICE_USER}" 750
  check_mode "$APP_DIR" "${SERVICE_USER}:${SERVICE_USER}" 755
  echo "    .env (root, 600), ${DATA_DIR} (${SERVICE_USER}, 750) e ${APP_DIR} (${SERVICE_USER}, 755) corretos."

  echo "==> 10/12: Inicializando o banco de dados (criacao das tabelas)"
  init_database
  verify_database "$db_path"

  echo "==> 11/12: Configurando o servico systemd"
  install -m 644 -o root -g root "$APP_DIR/deploy/systemd/${SERVICE_NAME}.service" "/etc/systemd/system/${SERVICE_NAME}.service"
  systemctl daemon-reload
  systemctl enable "$SERVICE_NAME"
  systemctl restart "$SERVICE_NAME"

  echo "==> 12/12: Configurando o Nginx"
  install -m 644 -o root -g root "$APP_DIR/deploy/nginx/${SERVICE_NAME}.conf" "/etc/nginx/sites-available/${SERVICE_NAME}.conf"
  ln -sf "/etc/nginx/sites-available/${SERVICE_NAME}.conf" "/etc/nginx/sites-enabled/${SERVICE_NAME}.conf"
  # Remove o site padrao do Nginx, se ainda estiver habilitado, para evitar conflito.
  rm -f /etc/nginx/sites-enabled/default
  nginx -t
  systemctl enable nginx
  if systemctl is-active --quiet nginx; then systemctl reload nginx; else systemctl start nginx; fi

  echo ""
  echo "===================================================================="
  echo " Instalacao concluida. Verificando saude da aplicacao localmente..."
  echo "===================================================================="
  if ! wait_for_health http://127.0.0.1:8000/health; then
    journalctl -u "$SERVICE_NAME" -n 30 --no-pager || true
    die "health check da API (127.0.0.1:8000) falhou. Verifique: systemctl status ${SERVICE_NAME}"
  fi
  echo "    API respondendo em 127.0.0.1:8000"
  wait_for_health http://127.0.0.1/health \
    || die "API OK, mas o Nginx (porta 80) nao encaminhou /health. Verifique: nginx -t e /var/log/nginx/${SERVICE_NAME}.error.log"
  echo "    Nginx encaminhando corretamente na porta 80"
  echo ""
  echo "Teste externo (substitua pelo IP publico da VM):"
  echo "  curl http://<IP-PUBLICO-DA-VM>/health"
}

if [[ "${BASH_SOURCE[0]:-$0}" == "$0" ]]; then
  main "$@"
fi
