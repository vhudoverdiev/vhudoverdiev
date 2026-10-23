#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo 'Run as root: bash deploy/setup_server.sh' >&2
  exit 1
fi
if [[ ! -r /etc/os-release ]]; then
  echo 'Cannot identify the server operating system.' >&2
  exit 1
fi
. /etc/os-release
if [[ "${ID:-}" != ubuntu && "${ID:-}" != debian ]]; then
  echo "This setup script supports Debian/Ubuntu; detected ${ID:-unknown}." >&2
  exit 1
fi

DOMAIN=vhudoverdiev.ru
APP_DIR=/opt/vhiti
ENV_DIR=/etc/vhiti
NGINX_AVAILABLE=/etc/nginx/sites-available/vhiti
NGINX_ENABLED=/etc/nginx/sites-enabled/vhiti
STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="/root/vhiti-setup-backup-$STAMP"

mkdir -p "$BACKUP_DIR"
cp -a /etc/nginx "$BACKUP_DIR/nginx" 2>/dev/null || true
systemctl list-units --type=service --all > "$BACKUP_DIR/services.txt"
nginx -T > "$BACKUP_DIR/nginx-full.txt" 2>&1 || true
if grep -Eq "server_name[^;]*(^|[[:space:]])(${DOMAIN}|www\\.${DOMAIN})([[:space:]]|;)|server_name[^;]*${DOMAIN//./\\.}" "$BACKUP_DIR/nginx-full.txt"; then
  echo "Existing Nginx config already mentions $DOMAIN. Nothing has been overwritten. Backup: $BACKUP_DIR" >&2
  exit 2
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip nginx mariadb-server git curl certbot python3-certbot-nginx
id -u vhiti >/dev/null 2>&1 || useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin vhiti
install -d -o vhiti -g vhiti "$APP_DIR/instance"
install -d -m 750 "$ENV_DIR"

if [[ -e "$APP_DIR" && ! -d "$APP_DIR/.git" ]]; then
  PREVIOUS_APP_DIR="${APP_DIR}.preexisting-${STAMP}"
  mv "$APP_DIR" "$PREVIOUS_APP_DIR"
  printf 'Moved pre-existing %s to %s
' "$APP_DIR" "$PREVIOUS_APP_DIR"
fi
if [[ ! -d "$APP_DIR/.git" ]]; then
  git clone https://github.com/vhudoverdiev/vhudoverdiev.git "$APP_DIR"
else
  git -C "$APP_DIR" remote get-url origin | grep -q 'github.com/vhudoverdiev/vhudoverdiev' || {
    PREVIOUS_APP_DIR="${APP_DIR}.preexisting-${STAMP}"
    mv "$APP_DIR" "$PREVIOUS_APP_DIR"
    printf 'Moved unrelated repository to %s
' "$PREVIOUS_APP_DIR"
    git clone https://github.com/vhudoverdiev/vhudoverdiev.git "$APP_DIR"
  }
  git -C "$APP_DIR" fetch origin main
  git -C "$APP_DIR" reset --hard origin/main
fi
chown -R vhiti:vhiti "$APP_DIR"

DB_PASS=$(openssl rand -hex 24)
APP_SECRET=$(openssl rand -hex 32)
mysql <<SQL
CREATE DATABASE IF NOT EXISTS vhiti CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'vhiti'@'localhost' IDENTIFIED BY '$DB_PASS';
ALTER USER 'vhiti'@'localhost' IDENTIFIED BY '$DB_PASS';
GRANT ALL PRIVILEGES ON vhiti.* TO 'vhiti'@'localhost';
FLUSH PRIVILEGES;
SQL
cat > "$ENV_DIR/vhiti.env" <<ENV
SECRET_KEY=$APP_SECRET
DATABASE_URL=mysql+pymysql://vhiti:$DB_PASS@127.0.0.1/vhiti?charset=utf8mb4
FLASK_DEBUG=0
ENV
chmod 640 "$ENV_DIR/vhiti.env"
chown root:vhiti "$ENV_DIR/vhiti.env"

sudo -u vhiti python3 -m venv "$APP_DIR/.venv"
sudo -u vhiti "$APP_DIR/.venv/bin/pip" install --disable-pip-version-check -r "$APP_DIR/requirements.txt"
sudo -u vhiti bash -c "cd '$APP_DIR' && set -a && . '$ENV_DIR/vhiti.env' && set +a && .venv/bin/flask --app wsgi.py db upgrade"
install -m 644 "$APP_DIR/deploy/vhiti.service" /etc/systemd/system/vhiti.service
systemctl daemon-reload
systemctl enable --now vhiti

install -m 644 "$APP_DIR/deploy/nginx-vhiti.conf" "$NGINX_AVAILABLE"
ln -sfn "$NGINX_AVAILABLE" "$NGINX_ENABLED"
nginx -t
systemctl reload nginx
ufw allow 'Nginx Full' 2>/dev/null || true

printf '\nInitial HTTP setup is complete. Backup: %s\n' "$BACKUP_DIR"
printf 'Create the first admin: sudo -u vhiti bash -lc "cd %s && set -a && . %s/vhiti.env && set +a && .venv/bin/flask --app wsgi.py create-admin"\n' "$APP_DIR" "$ENV_DIR"
printf 'After DNS points to this server, enable TLS: certbot --nginx -d %s\n' "$DOMAIN"
printf 'For deployment and course upload, run pdeploy from the configured Mac terminal.\n'
