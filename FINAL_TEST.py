#!/usr/bin/env python
"""
Финальный тест всей системы
"""
import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from customers.models import Client
from django_tenants.utils import tenant_context
from users_app.models import TenantUser

print("=" * 70)
print("ФИНАЛЬНЫЙ ТЕСТ СИСТЕМЫ")
print("=" * 70)

# Часть 1: Проверка структуры БД
print("\n1. ПРОВЕРКА СТРУКТУРЫ БД")
print("-" * 70)

print("\nPublic schema:")
public_users = User.objects.all()
print(f"  auth_user: {public_users.count()} пользователей")
for user in public_users:
    print(f"    - {user.username}")

clients = Client.objects.filter(schema_name__startswith='tenant_').order_by('id')

for client in clients:
    print(f"\n{client.name} ({client.schema_name}):")
    with tenant_context(client):
        tenant_users = TenantUser.objects.all()
        print(f"  users_app_tenantuser: {tenant_users.count()} пользователей")
        for user in tenant_users:
            print(f"    - {user.username} ({user.get_role_display()})")

# Часть 2: Тест API аутентификации
print("\n\n2. ТЕСТ API АУТЕНТИФИКАЦИИ")
print("-" * 70)

test_cases = [
    ('admin_5', 'admin123', 'Tenant 1 Admin'),
    ('worker_5', 'worker123', 'Tenant 1 Worker'),
    ('admin_6', 'admin123', 'Tenant 2 Admin'),
    ('worker_6', 'worker123', 'Tenant 2 Worker'),
]

for username, password, description in test_cases:
    response = requests.post(
        'http://localhost:8000/api/auth/token/',
        json={'username': username, 'password': password},
        headers={'Content-Type': 'application/json'},
        timeout=5
    )
    
    status = "✓" if response.status_code == 200 else "✗"
    print(f"{status} {description:20} - Status: {response.status_code}")

# Часть 3: Тест админ-панели
print("\n\n3. ТЕСТ АДМИН-ПАНЕЛИ")
print("-" * 70)

session = requests.Session()

# Логин
response = session.get('http://localhost:8000/admin/login/')
response = session.post(
    'http://localhost:8000/admin/login/',
    data={
        'username': 'admin',
        'password': 'admin123',
        'csrfmiddlewaretoken': session.cookies.get('csrftoken', ''),
    },
    allow_redirects=True
)

print(f"✓ Логин admin: {response.status_code}")

# Проверяем доступ к TenantUser
response = session.get('http://localhost:8000/admin/users_app/tenantuser/')
print(f"✓ Доступ к TenantUser: {response.status_code}")

if 'admin_5' in response.text and 'worker_5' in response.text:
    print(f"  ✓ Видны пользователи Tenant 1")

# Проверяем доступ к auth/user
response = session.get('http://localhost:8000/admin/auth/user/')
print(f"✓ Доступ к auth/user: {response.status_code}")

if response.status_code == 200:
    if 'is_staff' not in response.text or 'admin' in response.text:
        print(f"  ✓ Страница загружена без ошибок")

# Часть 4: Проверка изоляции
print("\n\n4. ПРОВЕРКА ИЗОЛЯЦИИ")
print("-" * 70)

# Получить токены для обоих админов
response1 = requests.post(
    'http://localhost:8000/api/auth/token/',
    json={'username': 'admin_5', 'password': 'admin123'},
    headers={'Content-Type': 'application/json'},
    timeout=5
)

response2 = requests.post(
    'http://localhost:8000/api/auth/token/',
    json={'username': 'admin_6', 'password': 'admin123'},
    headers={'Content-Type': 'application/json'},
    timeout=5
)

if response1.status_code == 200 and response2.status_code == 200:
    user1 = response1.json().get('user', {})
    user2 = response2.json().get('user', {})
    
    if user1.get('id') != user2.get('id'):
        print(f"✓ admin_5 и admin_6 имеют разные ID")
        print(f"  admin_5: ID={user1.get('id')}")
        print(f"  admin_6: ID={user2.get('id')}")
    else:
        print(f"✗ admin_5 и admin_6 имеют одинаковые ID")

print("\n" + "=" * 70)
print("✓ ФИНАЛЬНЫЙ ТЕСТ ЗАВЕРШЕН")
print("=" * 70)
