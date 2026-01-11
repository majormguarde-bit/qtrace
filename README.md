# Django Multi-Tenancy Project (SKKP)

Проект с поддержкой мульти-арендности на базе Django и django-tenants.

## Архитектура

- **Подход**: Shared Database, Separate Schemas
- **Изоляция**: Каждый клиент имеет отдельную схему в одной БД
- **Маршрутизация**: По поддоменам (tenant1.localhost, tenant2.localhost)

## Структура приложений

### SHARED_APPS (Public Schema)
- `django_tenants` - основная библиотека
- `customers` - управление клиентами и доменами
- Django admin, auth, contenttypes и т.д.

### TENANT_APPS (Tenant Schemas)
- `tasks` - управление задачами
- `users_app` - управление пользователями
- `media_app` - управление медиа-файлами

## Требования

- Python 3.13+
- PostgreSQL 12+

## Установка

1. Активировать виртуальное окружение:
```bash
.\venv\Scripts\activate
```

2. Установить зависимости:
```bash
pip install -r requirements.txt
```

3. Настроить БД в `.env` файле

4. Создать миграции:
```bash
python manage.py makemigrations
```

5. Применить миграции (создаст public schema):
```bash
python manage.py migrate_schemas --shared
```

## Использование

### Создание клиента через shell

```bash
python manage.py shell
```

```python
from customers.models import Client, Domain

# Создать клиента
client = Client.objects.create(name='Tenant 1')

# Создать домен для клиента
Domain.objects.create(
    domain='tenant1.localhost',
    tenant=client,
    is_primary=True
)
```

### Запуск сервера

```bash
python manage.py runserver 0.0.0.0:8000
```

Затем обратиться к:
- `http://tenant1.localhost:8000` - для первого тенанта
- `http://tenant2.localhost:8000` - для второго тенанта

## Миграции

Для применения миграций ко всем тенантам:
```bash
python manage.py migrate_schemas
```

Для применения только к public schema:
```bash
python manage.py migrate_schemas --shared
```
