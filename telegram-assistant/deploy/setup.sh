#!/usr/bin/env bash
# Ubuntu serverga (Amazon Lightsail) o'rnatish skripti.
# Loyiha /home/ubuntu/telegram-assistant ga ko'chirilgan deb hisoblanadi.
# Ishlatish:  bash deploy/setup.sh
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

echo "==> Tizim paketlari o'rnatilmoqda (python)..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip

echo "==> Virtual muhit yaratilmoqda..."
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    echo "!!! .env fayli yaratildi — uni tahrirlab BOT_TOKEN, OWNER_ID va"
    echo "!!! GEMINI_API_KEY qiymatlarini kiriting:  nano .env"
fi

echo "==> systemd service o'rnatilmoqda..."
# Service fayldagi yo'llarni haqiqiy joylashuvga moslaymiz
sudo bash -c "sed -e 's|/home/ubuntu/telegram-assistant|$APP_DIR|g' \
    -e 's|^User=.*|User=$(whoami)|' \
    '$APP_DIR/deploy/assistant.service' > /etc/systemd/system/assistant.service"
sudo systemctl daemon-reload
sudo systemctl enable assistant

echo ""
echo "Tayyor! Endi:"
echo "  1) nano .env          — kalitlarni kiriting"
echo "  2) sudo systemctl start assistant"
echo "  3) sudo journalctl -u assistant -f   — loglarni kuzatish"
