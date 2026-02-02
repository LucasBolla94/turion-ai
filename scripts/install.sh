#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/bot-ai"
SERVICE_FILE="/etc/systemd/system/bot-ai.service"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo ./install.sh"
  exit 1
fi

apt-get update -y
apt-get install -y python3 python3-venv python3-pip curl

mkdir -p "$APP_DIR"
cp -r ./* "$APP_DIR"

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

cp scripts/bot-ai.service "$SERVICE_FILE"

systemctl daemon-reload
systemctl enable bot-ai.service
systemctl restart bot-ai.service

echo "Installed and started bot-ai.service"
