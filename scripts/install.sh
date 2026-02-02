#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/bot-ai"
SERVICE_FILE="/etc/systemd/system/bot-ai.service"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo ./install.sh"
  exit 1
fi

mkdir -p "$APP_DIR"
cp -r ./* "$APP_DIR"
cp scripts/bot-ai.service "$SERVICE_FILE"

systemctl daemon-reload
systemctl enable bot-ai.service
systemctl restart bot-ai.service

echo "Installed and started bot-ai.service"
