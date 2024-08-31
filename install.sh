#!/bin/bash

if [ "$(id -u)" -ne "0" ]; then
    echo "Этот скрипт нужно запускать с правами суперпользователя (sudo)."
    exit 1
fi


VENV_DIR="venv"
REQUIREMENTS_FILE="requirements.txt"

python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install -r "$REQUIREMENTS_FILE"

deactivate


SERVISE_USER="ianus"

sudo useradd -r -s /sbin/nologin $SERVISE_USER

SCRIPT_DIR=$(pwd)
VENV_PATH="${SCRIPT_DIR}/venv/bin/python"
PYTHON_SCRIPT_PATH="${SCRIPT_DIR}/main.py"
WORKING_DIR="${SCRIPT_DIR}"

PROJECT_SERVICE_FILE_PATH="${SCRIPT_DIR}/ianus.service"

cat <<EOF > "$PROJECT_SERVICE_FILE_PATH"
[Unit]
Description=Ianus - attendance bot
After=network.target

[Service]
Type=simple
ExecStart=$VENV_PATH $PYTHON_SCRIPT_PATH
WorkingDirectory=$WORKING_DIR
Environment="PATH=${SCRIPT_DIR}/venv/bin"
Restart=always
User=$SERVISE_USER
Group=$SERVISE_USER

[Install]
WantedBy=multi-user.target
EOF


SYSTEMD_SERVICE_LINK="/etc/systemd/system/ianus.service"
ln -sf "$PROJECT_SERVICE_FILE_PATH" "$SYSTEMD_SERVICE_LINK"

systemctl daemon-reload

echo "Запуск сервиса..."
systemctl start my_service.service
systemctl enable my_service.service

sleep 5

systemctl status my_service.service
