#!/bin/sh
#Starting all containers

# Читаем MODE из .env, если не установлен в окружении
if [ -z "$MODE" ]; then
    if [ -f ".env" ]; then
        MODE=$(grep "^MODE=" .env | cut -d '=' -f2)
    fi
    # Если MODE все еще пустой, используем dev по умолчанию
    MODE="${MODE:-dev}"
fi

echo "[!] Starting quiz in $MODE mode"

sudo docker compose up -d --build

sudo docker ps -a
