#!/usr/bin/env python
"""
Тест логина в админ-панель
"""
import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from customers.models import Client
from django_tenants.utils import tenant_context

# Проверить, есть ли пользователи в public schema
print("Пользователи в public schema:")
for user in User.objects.all():
    print(f"  - {user.username}")

print("\n" + "=" * 60)

# Проверить пользователей в каждом тенанте
clients = Client.objects.filter(schema_name__startswith='tenant_').order_by('id')

for client in clients:
    print(f"\nПользователи в {client.name} ({client.schema_name}):")
    with tenant_context(client):
        from users_app.models import TenantUser
        for user in TenantUser.objects.all():
            print(f"  - {user.username} ({user.get_role_display()})")

print("\n" + "=" * 60)
print("\nТестирование логина в админ-панель через localhost")

# Попытка логина в админ-панель
session = requests.Session()

# Получить CSRF токен
response = session.get('http://localhost:8000/admin/login/')
print(f"\nПолучение CSRF токена: {response.status_code}")

# Попытка логина
response = session.post(
    'http://localhost:8000/admin/login/',
    data={
        'username': 'admin',
        'password': 'admin123',
        'csrfmiddlewaretoken': session.cookies.get('csrftoken', ''),
    },
    allow_redirects=False
)

print(f"Логин admin: {response.status_code}")
if response.status_code == 302:
    print(f"  Редирект на: {response.headers.get('Location')}")
else:
    print(f"  Response: {response.text[:200]}")
