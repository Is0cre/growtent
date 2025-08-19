#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

sudo apt-get update
sudo apt-get install -y python3-venv python3-pip python3-dev libatlas-base-dev \
                        i2c-tools python3-smbus

# Enable I2C if not already
sudo raspi-config nonint do_i2c 0 || true

# Controller venv
cd "$ROOT/controller"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

echo "✅ Deps installed."
