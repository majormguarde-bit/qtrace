#!/usr/bin/env python
"""
Тестирование аутентификации пользователей тенанта.
Проверяет, что:
1. admin_5 может логиниться в Tenant 1
2. admin_6 может логиниться в Tenant 2
3. admin_5 НЕ может логиниться в Tenant 2
4. admin_6 НЕ может логиниться в Tenant 1
"""
import os
import django
import requests
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

BASE_URL = 'http://localhost:8000'

# Тестовые данные
test_cases = [
    {
        'name': 'Tenant 1 - admin_5 login',
        'host': 'tenant1.localhost:8000',
        'username': 'admin_5',
        'password': 'admin123',
        'should_succeed': True,
    },
    {
        'name': 'Tenant 1 - worker_5 login',
        'host': 'tenant1.localhost:8000',
        'username': 'worker_5',
        'password': 'worker123',
        'should_succeed': True,
    },
    {
        'name': 'Tenant 2 - admin_6 login',
        'host': 'tenant2.localhost:8000',
        'username': 'admin_6',
        'password': 'admin123',
        'should_succeed': True,
    },
    {
        'name': 'Tenant 2 - worker_6 login',
        'host': 'tenant2.localhost:8000',
        'username': 'worker_6',
        'password': 'worker123',
        'should_succeed': True,
    },
    {
        'name': 'Tenant 1 - admin_6 login (should fail)',
        'host': 'tenant1.localhost:8000',
        'username': 'admin_6',
        'password': 'admin123',
        'should_succeed': False,
    },
    {
        'name': 'Tenant 2 - admin_5 login (should fail)',
        'host': 'tenant2.localhost:8000',
        'username': 'admin_5',
        'password': 'admin123',
        'should_succeed': False,
    },
]

print("Тестирование аутентификации пользователей тенанта\n")
print("=" * 60)

for test in test_cases:
    print(f"\nТест: {test['name']}")
    print(f"Host: {test['host']}")
    print(f"Username: {test['username']}")
    
    url = f"http://{test['host']}/api/auth/token/"
    
    try:
        response = requests.post(
            url,
            json={
                'username': test['username'],
                'password': test['password'],
            },
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if test['should_succeed']:
                print(f"✓ УСПЕХ: Получен токен")
                print(f"  User: {data.get('user', {}).get('username')}")
                print(f"  Role: {data.get('user', {}).get('role')}")
            else:
                print(f"✗ ОШИБКА: Логин не должен был пройти, но прошел!")
        else:
            if not test['should_succeed']:
                print(f"✓ УСПЕХ: Логин отклонен (статус {response.status_code})")
            else:
                print(f"✗ ОШИБКА: Логин не прошел (статус {response.status_code})")
                print(f"  Response: {response.text}")
    
    except Exception as e:
        print(f"✗ ОШИБКА: {str(e)}")

print("\n" + "=" * 60)
print("Тестирование завершено")
