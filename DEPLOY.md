# Инструкция по деплою SKKP

## 1. Подготовка сервера (Ubuntu/Debian)
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv postgresql nginx certbot python3-certbot-nginx -y
```

## 2. База данных
Создайте БД в PostgreSQL (обязательно с расширением для схем, которое использует django-tenants):
```sql
CREATE DATABASE skkp_db;
CREATE USER skkp_user WITH PASSWORD 'your-password';
ALTER ROLE skkp_user SET client_encoding TO 'utf8';
ALTER ROLE skkp_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE skkp_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE skkp_db TO skkp_user;
```

## 3. Клонирование и настройка
```bash
git clone <your-repo-url>
cd skkp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Отредактируйте .env (укажите свои ключи и данные БД)
nano .env
```

## 4. Миграции (Важно для Multi-tenancy)
```bash
python manage.py migrate_schemas --shared
# После создания первого тенанта (публичного) через shell:
python manage.py create_tenant_superuser
```

## 5. Статика и Gunicorn
```bash
python manage.py collectstatic
gunicorn --bind 0.0.0.0:8000 config.wsgi:application
```

## 6. SSL (Wildcard)
Для работы поддоменов через HTTPS рекомендуется использовать Wildcard сертификат:
```bash
sudo certbot certonly --manual -d *.yourdomain.com -d yourdomain.com --preferred-challenges dns
```
