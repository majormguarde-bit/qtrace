#!/usr/bin/env python
"""
Полный тест аутентификации и изоляции тенантов
"""
import os
import django
import requests
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from customers.models import Client
from django_tenants.utils import tenant_context
from users_app.models import TenantUser

print("=" * 70)
print("ПОЛНЫЙ ТЕСТ АУТЕНТИФИКАЦИИ И ИЗОЛЯЦИИ ТЕНАНТОВ")
print("=" * 70)

# Часть 1: Проверка данных в БД
print("\n1. ПРОВЕРКА ДАННЫХ В БД")
print("-" * 70)

clients = Client.objects.filter(schema_name__startswith='tenant_').order_by('id')

for client in clients:
    print(f"\n{client.name} ({client.schema_name}):")
    with tenant_context(client):
        users = TenantUser.objects.all()
        print(f"  Всего пользователей: {users.count()}")
        for user in users:
            print(f"    - {user.username:15} | Role: {user.get_role_display():15} | Active: {user.is_active}")

# Часть 2: Тест API аутентификации
print("\n\n2. ТЕСТ API АУТЕНТИФИКАЦИИ")
print("-" * 70)

test_cases = [
    ('admin_5', 'admin123', 'Tenant 1 Admin'),
    ('worker_5', 'worker123', 'Tenant 1 Worker'),
    ('admin_6', 'admin123', 'Tenant 2 Admin'),
    ('worker_6', 'worker123', 'Tenant 2 Worker'),
    ('admin_5', 'wrongpass', 'Wrong Password'),
    ('nonexistent', 'password', 'Non-existent User'),
]

for username, password, description in test_cases:
    response = requests.post(
        'http://localhost:8000/api/auth/token/',
        json={'username': username, 'password': password},
        headers={'Content-Type': 'application/json'},
        timeout=5
    )
    
    status = "✓ SUCCESS" if response.status_code == 200 else "✗ FAILED"
    print(f"\n{description:25} | {status:15} | Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        user_data = data.get('user', {})
        print(f"  Username: {user_data.get('username')}")
        print(f"  Role: {user_data.get('role')}")
        print(f"  Token: {data.get('access', '')[:50]}...")

# Часть 3: Тест использования токена
print("\n\n3. ТЕСТ ИСПОЛЬЗОВАНИЯ ТОКЕНА")
print("-" * 70)

# Получить токен для admin_5
response = requests.post(
    'http://localhost:8000/api/auth/token/',
    json={'username': 'admin_5', 'password': 'admin123'},
    headers={'Content-Type': 'application/json'},
    timeout=5
)

if response.status_code == 200:
    token = response.json().get('access')
    
    # Использовать токен для получения данных пользователя
    response = requests.get(
        'http://localhost:8000/api/users/me/',
        headers={'Authorization': f'Bearer {token}'},
        timeout=5
    )
    
    print(f"\nПолучение данных пользователя (GET /api/users/me/):")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        user_data = response.json()
        print(f"  ✓ Успешно получены данные:")
        print(f"    - Username: {user_data.get('username')}")
        print(f"    - Email: {user_data.get('email')}")
        print(f"    - Role: {user_data.get('role')}")
    else:
        print(f"  ✗ Ошибка: {response.text}")

# Часть 4: Проверка изоляции
print("\n\n4. ПРОВЕРКА ИЗОЛЯЦИИ ТЕНАНТОВ")
print("-" * 70)

print("\nПроверка: admin_5 и admin_6 - разные пользователи в разных тенантах")

# Получить данные admin_5
response1 = requests.post(
    'http://localhost:8000/api/auth/token/',
    json={'username': 'admin_5', 'password': 'admin123'},
    headers={'Content-Type': 'application/json'},
    timeout=5
)

# Получить данные admin_6
response2 = requests.post(
    'http://localhost:8000/api/auth/token/',
    json={'username': 'admin_6', 'password': 'admin123'},
    headers={'Content-Type': 'application/json'},
    timeout=5
)

if response1.status_code == 200 and response2.status_code == 200:
    user1 = response1.json().get('user', {})
    user2 = response2.json().get('user', {})
    
    print(f"\nadmin_5:")
    print(f"  ID: {user1.get('id')}")
    print(f"  Username: {user1.get('username')}")
    print(f"  Role: {user1.get('role')}")
    
    print(f"\nadmin_6:")
    print(f"  ID: {user2.get('id')}")
    print(f"  Username: {user2.get('username')}")
    print(f"  Role: {user2.get('role')}")
    
    if user1.get('id') != user2.get('id'):
        print(f"\n✓ УСПЕХ: Пользователи имеют разные ID (изоляция работает)")
    else:
        print(f"\n✗ ОШИБКА: Пользователи имеют одинаковые ID")

print("\n" + "=" * 70)
print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
print("=" * 70)
