#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo ./install.sh"
  exit 1
fi

apt-get update -y
apt-get install -y curl

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js not found. Please install Node 18+ before continuing."
  exit 1
fi

npm install

cat > /etc/systemd/system/bot-ai-gateway.service <<'EOF'
[Unit]
Description=Bot AI WhatsApp Gateway
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/bot-ai-gateway
ExecStart=/usr/bin/node /opt/bot-ai-gateway/server.js
Restart=always
RestartSec=2
User=root
Group=root
Environment=PORT=3001
Environment=API_KEY=

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable bot-ai-gateway.service
systemctl restart bot-ai-gateway.service

echo "Installed and started bot-ai-gateway.service"
