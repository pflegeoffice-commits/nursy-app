#!/bin/bash
# ============================================================
#  Nursy – Hetzner Server Setup
#  Einmal ausführen: bash hetzner-setup.sh
# ============================================================
set -e

APP_DIR="/opt/nursy"
SERVICE_NAME="nursy"

echo ""
echo "=== [1/6] System-Pakete installieren ==="
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv git ufw

echo ""
echo "=== [2/6] Python-Abhängigkeiten installieren ==="
cd "$APP_DIR"
pip3 install -r requirements.txt

echo ""
echo "=== [3/6] Uploads-Ordner anlegen ==="
mkdir -p "$APP_DIR/uploads"
mkdir -p "$APP_DIR/formulare"

echo ""
echo "=== [4/6] Systemd-Service einrichten ==="
cat > /etc/systemd/system/${SERVICE_NAME}.service << 'EOF'
[Unit]
Description=Nursy Akut Plus Pflege App
After=network.target

[Service]
User=root
WorkingDirectory=/opt/nursy
EnvironmentFile=/opt/nursy/.env
ExecStart=/usr/bin/python3 server.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ${SERVICE_NAME}

echo ""
echo "=== [5/6] Firewall konfigurieren ==="
ufw allow 22/tcp    comment "SSH"
ufw allow 5000/tcp  comment "Nursy App"
ufw --force enable

echo ""
echo "=== [6/6] Service starten ==="
systemctl restart ${SERVICE_NAME}
sleep 2
systemctl status ${SERVICE_NAME} --no-pager

echo ""
echo "============================================================"
echo " Setup abgeschlossen!"
echo " App erreichbar unter: http://178.105.53.33:5000/"
echo "============================================================"
