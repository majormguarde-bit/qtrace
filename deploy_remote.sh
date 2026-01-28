#!/bin/bash

# Настройки
PROJECT_DIR="domains/qtrace.ru"
DB_NAME="s1147486_skkp"
DB_USER="s1147486_skkp"
DB_PASS="auydam27%q3bkxL29"

echo "--- Начинаем деплой SKKP на Sprinthost ---"

cd ~/$PROJECT_DIR

# 1. Распаковка (если загружен zip)
if [ -f "deploy.zip" ]; then
    echo "Распаковка архива..."
    unzip -o deploy.zip
    rm deploy.zip
fi

# 2. Настройка виртуального окружения
# На Sprinthost виртуальное окружение обычно в папке virtualenv уровнем выше
VENV_DIR="../../virtualenv/python3.10" # Путь может отличаться, уточните в панели
if [ ! -d "$VENV_DIR" ]; then
    echo "Создание виртуального окружения..."
    python3 -m venv ../../virtualenv/python3.10
fi
source ../../virtualenv/python3.10/bin/activate

# 3. Установка зависимостей
echo "Установка зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Создание .env
echo "Настройка .env..."
cat <<EOF > .env
DEBUG=False
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')
ALLOWED_HOSTS=qtrace.ru,.qtrace.ru,localhost
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASS
DB_HOST=localhost
DB_PORT=5432
EOF

# 5. Миграции и статика
echo "Миграции базы данных..."
python manage.py migrate_schemas --shared

echo "Сборка статики..."
python manage.py collectstatic --noinput

# 6. Перезапуск Passenger
mkdir -p tmp
touch tmp/restart.txt

echo "--- Деплой завершен! ---"
echo "Теперь создайте публичного тенанта командой:"
echo "python manage.py create_tenant_superuser"
