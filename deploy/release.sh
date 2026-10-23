#!/usr/bin/env bash
set -Eeuo pipefail
cd /opt/vhiti
git fetch origin main
git reset --hard origin/main
.venv/bin/pip install --disable-pip-version-check -r requirements.txt
set -a
. /etc/vhiti/vhiti.env
set +a
.venv/bin/flask --app wsgi.py db upgrade
.venv/bin/flask --app wsgi.py retire-ai-course --delete-media
systemctl restart vhiti
systemctl is-active --quiet vhiti
curl --fail --silent --show-error --max-time 15 -H 'Host: vhudoverdiev.ru' http://127.0.0.1/ >/dev/null
printf '%s\n' 'Release deployed and HTTP health check passed.'
