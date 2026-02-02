#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/bot-ai"
GATEWAY_DIR="/opt/bot-ai-gateway"
SERVICE_FILE="/etc/systemd/system/bot-ai.service"
GATEWAY_SERVICE_FILE="/etc/systemd/system/bot-ai-gateway.service"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo ./install.sh"
  exit 1
fi

apt-get update -y
apt-get install -y python3 python3-venv python3-pip curl ca-certificates tar postgresql openssl

install_node_lts() {
  if command -v node >/dev/null 2>&1; then
    return 0
  fi

  python3 - <<'PY'
import json
import sys
import urllib.request

url = "https://nodejs.org/dist/index.json"
with urllib.request.urlopen(url, timeout=10) as resp:
    data = json.loads(resp.read().decode("utf-8"))

for entry in data:
    v = entry["version"]
    if v.startswith("v24") and entry.get("lts"):
        print(v)
        break
else:
    print("", file=sys.stderr)
    sys.exit(1)
PY

  VERSION=$(python3 - <<'PY'
import json
import urllib.request

url = "https://nodejs.org/dist/index.json"
with urllib.request.urlopen(url, timeout=10) as resp:
    data = json.loads(resp.read().decode("utf-8"))

for entry in data:
    v = entry["version"]
    if v.startswith("v24") and entry.get("lts"):
        print(v)
        break
PY
  )

  if [[ -z "${VERSION}" ]]; then
    echo "Failed to resolve Node.js LTS version"
    exit 1
  fi

  ARCH=$(uname -m)
  case "$ARCH" in
    x86_64) PLATFORM="linux-x64" ;;
    aarch64|arm64) PLATFORM="linux-arm64" ;;
    *) echo "Unsupported arch: $ARCH"; exit 1 ;;
  esac

  BASE_URL="https://nodejs.org/dist/${VERSION}"
  TARBALL="node-${VERSION}-${PLATFORM}.tar.xz"
  TMP_DIR=$(mktemp -d)

  curl -fsSL "$BASE_URL/$TARBALL" -o "$TMP_DIR/$TARBALL"
  curl -fsSL "$BASE_URL/SHASUMS256.txt" -o "$TMP_DIR/SHASUMS256.txt"

  (cd "$TMP_DIR" && grep " $TARBALL$" SHASUMS256.txt | sha256sum -c -)

  mkdir -p /usr/local/lib/nodejs
  tar -xJf "$TMP_DIR/$TARBALL" -C /usr/local/lib/nodejs

  ln -sf "/usr/local/lib/nodejs/node-${VERSION}-${PLATFORM}/bin/node" /usr/local/bin/node
  ln -sf "/usr/local/lib/nodejs/node-${VERSION}-${PLATFORM}/bin/npm" /usr/local/bin/npm
  ln -sf "/usr/local/lib/nodejs/node-${VERSION}-${PLATFORM}/bin/npx" /usr/local/bin/npx

  rm -rf "$TMP_DIR"
}

install_node_lts

open_firewall_ports() {
  # Gateway port (WhatsApp)
  local PORT="3001"

  if command -v ufw >/dev/null 2>&1; then
    if ufw status | grep -qi "Status: active"; then
      ufw allow "${PORT}/tcp" >/dev/null 2>&1 || true
    fi
  fi

  if command -v firewall-cmd >/dev/null 2>&1; then
    if firewall-cmd --state >/dev/null 2>&1; then
      firewall-cmd --permanent --add-port="${PORT}/tcp" >/dev/null 2>&1 || true
      firewall-cmd --reload >/dev/null 2>&1 || true
    fi
  fi
}

open_firewall_ports

mkdir -p "$APP_DIR"
# copy including dotfiles (like .env.example)
shopt -s dotglob
cp -r ./* "$APP_DIR"
shopt -u dotglob

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

if [[ ! -f "$APP_DIR/.env" ]]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
fi

DB_PASSWORD=$(grep -E '^DB_PASSWORD=' "$APP_DIR/.env" | cut -d'=' -f2-)
if [[ -z "$DB_PASSWORD" ]]; then
  DB_PASSWORD=$(openssl rand -hex 16)
  sed -i "s/^DB_PASSWORD=.*/DB_PASSWORD=$DB_PASSWORD/" "$APP_DIR/.env"
fi

# postgres setup (local-only)
DB_NAME=$(grep -E '^DB_NAME=' "$APP_DIR/.env" | cut -d'=' -f2-)
DB_USER=$(grep -E '^DB_USER=' "$APP_DIR/.env" | cut -d'=' -f2-)

sudo -u postgres psql -tAc "select 1 from pg_roles where rolname='$DB_USER'" | grep -q 1 || \
  sudo -u postgres psql -c "create user $DB_USER with password '$DB_PASSWORD';"

sudo -u postgres psql -tAc "select 1 from pg_database where datname='$DB_NAME'" | grep -q 1 || \
  sudo -u postgres psql -c "create database $DB_NAME owner $DB_USER;"

sudo -u postgres psql -d "$DB_NAME" -c "grant all privileges on database $DB_NAME to $DB_USER;"

psql "postgresql://$DB_USER:$DB_PASSWORD@127.0.0.1:5432/$DB_NAME" -f "$APP_DIR/docs/postgres.sql"

mkdir -p "$GATEWAY_DIR"
cp -r "$APP_DIR/gateway"/* "$GATEWAY_DIR"

if [[ ! -f "$GATEWAY_DIR/.env" ]]; then
  cat > "$GATEWAY_DIR/.env" <<'EOF'
PORT=3001
API_KEY=
EOF
fi

(cd "$GATEWAY_DIR" && npm install)

cp scripts/bot-ai.service "$SERVICE_FILE"
cp scripts/bot-ai-gateway.service "$GATEWAY_SERVICE_FILE"

cat > /usr/local/bin/turion <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd /opt/bot-ai
/opt/bot-ai/.venv/bin/python -m src.cli "$@"
EOF
chmod +x /usr/local/bin/turion

systemctl daemon-reload
systemctl enable bot-ai.service bot-ai-gateway.service
systemctl restart bot-ai.service bot-ai-gateway.service

echo "Installed and started bot-ai.service and bot-ai-gateway.service"

if [[ -t 1 ]]; then
  echo "Iniciando setup interativo..."
  cd /opt/bot-ai
  /opt/bot-ai/.venv/bin/python -m src.cli setup || true
else
  echo "Instalação sem TTY. Rode: turion setup"
fi
