#!/usr/bin/env python
"""
Тест доступа к админ-панели
"""
import requests

print("Тест доступа к админ-панели\n")
print("=" * 60)

session = requests.Session()

# Получить страницу логина
print("\n1. Получение страницы логина...")
response = session.get('http://localhost:8000/admin/login/')
print(f"   Status: {response.status_code}")

# Попытка логина
print("\n2. Попытка логина с admin/admin123...")
response = session.post(
    'http://localhost:8000/admin/login/',
    data={
        'username': 'admin',
        'password': 'admin123',
        'csrfmiddlewaretoken': session.cookies.get('csrftoken', ''),
    },
    allow_redirects=False
)

print(f"   Status: {response.status_code}")
if response.status_code == 302:
    print(f"   ✓ Редирект на: {response.headers.get('Location')}")
    
    # Попытка доступа к админ-панели
    print("\n3. Доступ к админ-панели...")
    response = session.get('http://localhost:8000/admin/')
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        print(f"   ✓ Админ-панель доступна")
        if 'Django administration' in response.text:
            print(f"   ✓ Содержимое админ-панели загружено")
    else:
        print(f"   ✗ Ошибка: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
else:
    print(f"   ✗ Ошибка логина")
    print(f"   Response: {response.text[:200]}")

print("\n" + "=" * 60)
