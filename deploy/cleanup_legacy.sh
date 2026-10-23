#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo 'Run as root.' >&2
  exit 1
fi

# Do not remove the current service until the replacement is available locally.
systemctl is-active --quiet vhiti || { echo 'New vhiti service is not active; legacy site was not touched.' >&2; exit 1; }
curl --fail --silent --show-error --max-time 10 -H 'Host: vhudoverdiev.ru' http://127.0.0.1/ >/dev/null || {
  echo 'New site health check failed; legacy site was not touched.' >&2
  exit 1
}

STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="/root/legacy-nginx-config-$STAMP"
install -d -m 700 "$BACKUP_DIR"
for path in \
  /etc/nginx/sites-available/peredacha.conf \
  /etc/nginx/sites-enabled/peredacha.conf \
  /etc/nginx/conf.d/peredacha-rate-limit.conf \
  /etc/systemd/system/gunicorn.service; do
  if [[ -e "$path" || -L "$path" ]]; then
    cp -a "$path" "$BACKUP_DIR/"
  fi
done

systemctl disable --now gunicorn.service
rm -f \
  /etc/nginx/sites-enabled/peredacha.conf \
  /etc/nginx/sites-available/peredacha.conf \
  /etc/nginx/conf.d/peredacha-rate-limit.conf
nginx -t
systemctl reload nginx

# The application and its database are explicitly identified from the inspected config.
if mariadb -NBe "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='peredacha'" | grep -qx peredacha; then
  mariadb -e 'DROP DATABASE peredacha'
fi
rm -rf -- /opt/peredacha
rm -f /etc/systemd/system/gunicorn.service
systemctl daemon-reload

if certbot certificates 2>/dev/null | grep -q 'Certificate Name: akvilon-peredacha.ru'; then
  certbot delete --cert-name akvilon-peredacha.ru --non-interactive
fi

printf 'Legacy Peredacha site removed. Nginx/systemd config snapshots: %s\n' "$BACKUP_DIR"
printf 'New service status: '
systemctl is-active vhiti
