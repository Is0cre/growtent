#!/usr/bin/env bash
set -euo pipefail
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$APP_DIR")"

cd "$APP_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# systemd service
SERVICE_FILE="/etc/systemd/system/growtent-flask.service"
sudo tee "$SERVICE_FILE" >/dev/null <<EOF
[Unit]
Description=Growtent Flask
After=network-online.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${APP_DIR}
Environment=GROWTENT_ROOT=${ROOT_DIR}
ExecStart=${APP_DIR}/.venv/bin/gunicorn -b 0.0.0.0:5000 "app:create_app()"
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now growtent-flask.service
echo "✅ Deployed. Service: growtent-flask (port 5000)"
