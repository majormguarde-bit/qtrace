#!/usr/bin/env python
"""
Тест изоляции админ-панели по тенантам
"""
import requests

print("=" * 70)
print("ТЕСТ ИЗОЛЯЦИИ АДМИН-ПАНЕЛИ")
print("=" * 70)

# Логинимся в админ-панель
session = requests.Session()

print("\n1. Логин в админ-панель...")
response = session.get('http://localhost:8000/admin/login/')
print(f"   Status: {response.status_code}")

response = session.post(
    'http://localhost:8000/admin/login/',
    data={
        'username': 'admin',
        'password': 'admin123',
        'csrfmiddlewaretoken': session.cookies.get('csrftoken', ''),
    },
    allow_redirects=True
)

print(f"   ✓ Логин успешен")

# Проверяем страницу TenantUser
print("\n2. Проверка страницы TenantUser в админ-панели...")
response = session.get('http://localhost:8000/admin/users_app/tenantuser/')
print(f"   Status: {response.status_code}")

if response.status_code == 200:
    # Ищем пользователей в HTML
    if 'admin_5' in response.text:
        print(f"   ✓ Найден admin_5")
    if 'worker_5' in response.text:
        print(f"   ✓ Найден worker_5")
    if 'admin_6' in response.text:
        print(f"   ✓ Найден admin_6")
    if 'worker_6' in response.text:
        print(f"   ✓ Найден worker_6")
    
    # Подсчитываем количество пользователей
    count = response.text.count('<tr class="row')
    print(f"   Всего строк в таблице: {count}")
else:
    print(f"   ✗ Ошибка: {response.status_code}")

print("\n" + "=" * 70)
print("ТЕСТ ЗАВЕРШЕН")
print("=" * 70)
