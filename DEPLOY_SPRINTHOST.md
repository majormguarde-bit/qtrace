# Инструкция по развертыванию проекта SKKP на хостинге Sprinthost

В данной инструкции описаны шаги по деплою Django-приложения с использованием `django-tenants`, `Gunicorn`, `WhiteNoise` и переменных окружения.

## 1. Подготовка в панели Sprinthost

1. Перейдите в раздел **«Сайты»** и добавьте новый сайт (например, `qtrace.ru`).
2. В разделе **«Python»**:
    - Выберите версию **Python 3.12**.
    - Укажите путь к приложению: `domains/qtrace.ru/public_html/skkp`.
    - Тип приложения: **Django**.

## 2. Клонирование и настройка окружения (через SSH)

Подключитесь к серверу по SSH и выполните команды:

```bash
# Переход в директорию сайта
cd domains/qtrace.ru/public_html/

# Клонирование репозитория
git clone https://github.com/majormguarde-bit/qtrace.git skkp
cd skkp

# Создание виртуального окружения
python -m venv .venv
source .venv/bin/activate

# Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. База данных и переменные окружения

1. Создайте базу данных **PostgreSQL** в панели управления Sprinthost.
2. Создайте файл `.env` в корне проекта на сервере:

```bash
cp .env.example .env
nano .env
```

3. Заполните `.env` актуальными данными:
```env
SECRET_KEY='ваш-секретный-ключ'
DEBUG=False
ALLOWED_HOSTS=qtrace.ru,*.qtrace.ru,localhost
DB_NAME=имя_бд
DB_USER=пользователь
DB_PASSWORD=пароль
DB_HOST=localhost
DB_PORT=5432
```

## 4. Миграции и статичные файлы

В активированном виртуальном окружении выполните:

```bash
# Применение миграций для всех схем (публичной и тенантов)
python manage.py migrate_schemas --noinput

# Сбор статичных файлов (CSS, JS, Images)
python manage.py collectstatic --noinput
```

## 5. Настройка Passenger WSGI

Для работы Django на Sprinthost создайте файл `passenger_wsgi.py` в директории `skkp/`:

```python
import os
import sys

# Путь к директории проекта
PROJECT_ROOT = '/home/ВАШ_ЛОГИН/domains/qtrace.ru/public_html/skkp'
sys.path.insert(0, PROJECT_ROOT)

# Путь к библиотекам виртуального окружения
os.environ['PYTHONPATH'] = f'{PROJECT_ROOT}/.venv/lib/python3.12/site-packages'
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

from config.wsgi import application
```

## 6. Инициализация публичной схемы (через shell)

Если база данных пустая, необходимо создать публичного тенанта:

```bash
python manage.py shell
```
```python
from customers.models import Client, Domain

# Создание публичного тенанта
tenant = Client(schema_name='public', name='Public Interface')
tenant.save()

# Привязка домена
domain = Domain(domain='qtrace.ru', tenant=tenant, is_primary=True)
domain.save()
```

## 7. Финализация

1. В панели Sprinthost (раздел Python) нажмите кнопку **«Перезагрузить»**.
2. Убедитесь, что для домена включена поддержка **Wildcard DNS** (поддомены `*.qtrace.ru`), чтобы работали личные кабинеты клиентов.

---
**Примечание:** Все изменения в коде (поддержка `.env` и WhiteNoise) уже интегрированы в репозиторий.
