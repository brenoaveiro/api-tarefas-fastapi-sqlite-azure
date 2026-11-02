#!/usr/bin/env bash
#
# https_ip.sh — Emite e instala um certificado TLS do Let's Encrypt para o IP PUBLICO da VM
# e configura a renovacao automatica.
#
# Requisitos (documentacao oficial, 2026): Certbot >= 5.4, perfil "shortlived" (~6 dias),
# desafio HTTP-01 via webroot na porta 80 e a opcao --ip-address. Os plugins nginx/apache do
# Certbot NAO instalam certificados de IP; por isso este script usa "certonly" + deploy hook.
#
# Uso (na VM, como root):
#   sudo ./deploy/https_ip.sh <IP-PUBLICO> --staging     # teste (certificado NAO confiavel)
#   sudo ./deploy/https_ip.sh <IP-PUBLICO>               # certificado real
#
# O script e idempotente e NAO desativa a protecao de escrita por IP do Nginx.
set -euo pipefail

IP="${1:?uso: $0 <IP-PUBLICO> [--staging]}"
MODO="${2:-}"
APP_DIR="/opt/api-tarefas"
VENV="/opt/certbot-venv"
WEBROOT="/var/www/letsencrypt"
LE_DIR="/etc/letsencrypt"
SITES="/etc/nginx/sites-available"

[[ "$EUID" -eq 0 ]] || { echo "Execute com sudo/root."; exit 1; }
[[ "$IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "IP invalido: $IP"; exit 1; }

echo "==> 1/7: Atualizando a configuracao base do Nginx (inclui o desafio ACME)"
cp -a "${SITES}/api-tarefas.conf" "${SITES}/api-tarefas.conf.bak.$(date -u +%Y%m%dT%H%M%SZ)"
install -m 644 -o root -g root "${APP_DIR}/deploy/nginx/api-tarefas.conf" "${SITES}/api-tarefas.conf"
install -d -m 755 -o root -g root "$WEBROOT"
nginx -t
systemctl reload nginx

echo "==> 2/7: Instalando o Certbot (>= 5.4) em ambiente virtual isolado"
if [[ ! -x "${VENV}/bin/certbot" ]]; then
  apt-get install -y python3-venv >/dev/null
  python3 -m venv "$VENV"
  "${VENV}/bin/pip" install --quiet --upgrade pip
  "${VENV}/bin/pip" install --quiet 'certbot>=5.4'
fi
VER="$("${VENV}/bin/certbot" --version | awk '{print $2}')"
"${VENV}/bin/python" - "$VER" <<'PY'
import sys
v = tuple(int(x) for x in sys.argv[1].split(".")[:2])
sys.exit(0 if v >= (5, 4) else 1)
PY
echo "    certbot ${VER}"

COMUM=(certonly --non-interactive --agree-tos --register-unsafely-without-email
       --preferred-profile shortlived --webroot -w "$WEBROOT" --ip-address "$IP")

if [[ "$MODO" == "--staging" ]]; then
  echo "==> 3/7: Teste no ambiente de STAGING (nao altera o Nginx)"
  "${VENV}/bin/certbot" "${COMUM[@]}" --staging --cert-name "${IP}-staging"
  "${VENV}/bin/certbot" certificates --cert-name "${IP}-staging" | grep -E "Certificate Name|Domains|Expiry"
  "${VENV}/bin/certbot" delete --non-interactive --cert-name "${IP}-staging" >/dev/null
  echo "Staging OK. Rode novamente sem --staging para emitir o certificado real."
  exit 0
fi

echo "==> 3/7: Emitindo o certificado REAL para ${IP}"
"${VENV}/bin/certbot" "${COMUM[@]}" --cert-name "$IP" --deploy-hook "systemctl reload nginx"
[[ -s "${LE_DIR}/live/${IP}/fullchain.pem" ]] || { echo "ERRO: certificado nao encontrado."; exit 1; }

echo "==> 4/7: Instalando o bloco HTTPS do Nginx"
sed "s/@@IP@@/${IP}/g" "${APP_DIR}/deploy/nginx/api-tarefas-https.conf" > "${SITES}/api-tarefas-https.conf"
chmod 644 "${SITES}/api-tarefas-https.conf"
ln -sf "${SITES}/api-tarefas-https.conf" /etc/nginx/sites-enabled/api-tarefas-https.conf
nginx -t
systemctl reload nginx

echo "==> 5/7: Configurando a renovacao automatica (timer systemd, duas vezes ao dia)"
cat > /etc/systemd/system/certbot-renew.service <<EOF
[Unit]
Description=Renovacao dos certificados Let's Encrypt (Certbot)
After=network-online.target nginx.service

[Service]
Type=oneshot
ExecStart=${VENV}/bin/certbot renew --quiet
EOF
cat > /etc/systemd/system/certbot-renew.timer <<'EOF'
[Unit]
Description=Executa a renovacao do Certbot duas vezes ao dia

[Timer]
OnCalendar=*-*-* 00,12:00:00
RandomizedDelaySec=600
Persistent=true

[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now certbot-renew.timer

echo "==> 6/7: Testando a renovacao (dry-run em staging)"
"${VENV}/bin/certbot" renew --dry-run --cert-name "$IP" | tail -3

echo "==> 7/7: Verificando o certificado servido"
echo | openssl s_client -connect "127.0.0.1:443" -servername "$IP" 2>/dev/null | openssl x509 -noout -subject -issuer -dates -ext subjectAltName
curl -fsS --max-time 10 "https://${IP}/health" && echo
echo "HTTPS configurado. Renovacao: systemctl list-timers certbot-renew.timer"
