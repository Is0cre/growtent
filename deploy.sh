#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/matthias/grow_tent_controller"
CTRL_VENV="${PROJECT_DIR}/.grow_tent_controller"
WEB_VENV="${PROJECT_DIR}/.grow_tent_web"

echo "[1/8] Controller venv..."
python3 -m venv "$CTRL_VENV"
source "${CTRL_VENV}/bin/activate"
pip install --upgrade pip
pip install -r "${PROJECT_DIR}/requirements.txt"
deactivate

echo "[2/8] Web venv (system site-packages ok)..."
python3 -m venv --system-site-packages "$WEB_VENV"
source "${WEB_VENV}/bin/activate"
pip install --upgrade pip
pip install -r "${PROJECT_DIR}/flask-app/requirements.txt"
# sanity check for numpy (matplotlib)
python - <<'PY'
try:
    import numpy, sys
    print("Using NumPy:", numpy.__version__, numpy.__file__)
except Exception as e:
    print("NumPy check:", e)
PY
deactivate

echo "[3/8] Optional camera packages..."
sudo apt update
sudo apt install -y python3-picamera2 libcamera-apps || true

echo "[4/8] Install services..."
sudo cp "${PROJECT_DIR}/service/growtent.service" /etc/systemd/system/growtent.service
sudo cp "${PROJECT_DIR}/service/growtent-web.service" /etc/systemd/system/growtent-web.service

echo "[5/8] Reload systemd..."
sudo systemctl daemon-reload

echo "[6/8] Enable services..."
sudo systemctl enable growtent.service
sudo systemctl enable growtent-web.service

echo "[7/8] Start/restart services..."
sudo systemctl restart growtent.service
sudo systemctl restart growtent-web.service

echo "[8/8] Done. UI at http://<pi-ip>:8000"
