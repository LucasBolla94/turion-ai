#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/LucasBolla94/turion-ai/archive/refs/heads/main.tar.gz"
TMP_DIR="/tmp/turion-ai-install"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo bash -c \"curl -fsSL http://turion.network/install.sh | bash\""
  exit 1
fi

apt-get update -y
apt-get install -y curl tar

rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"

curl -fsSL "$REPO_URL" -o "$TMP_DIR/src.tgz"

tar -xzf "$TMP_DIR/src.tgz" -C "$TMP_DIR"

# assume default github tar folder name
SRC_DIR="$TMP_DIR/turion-ai-main"

cd "$SRC_DIR"
chmod +x scripts/install.sh
./scripts/install.sh
