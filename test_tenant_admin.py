#!/usr/bin/env python
"""
Тест доступа админов тенантов к админ-панели
"""
import requests

print("=" * 70)
print("ТЕСТ ДОСТУПА АДМИНОВ ТЕНАНТОВ К АДМИН-ПАНЕЛИ")
print("=" * 70)

# Тест 1: Логин admin_5 через tenant1.localhost
print("\n1. Логин admin_5 через tenant1.localhost")
session = requests.Session()

response = session.get('http://tenant1.localhost:8000/admin/login/')
print(f"   Получение страницы логина: {response.status_code}")

response = session.post(
    'http://tenant1.localhost:8000/admin/login/',
    data={
        'username': 'admin_5',
        'password': 'admin123',
        'csrfmiddlewaretoken': session.cookies.get('csrftoken', ''),
    },
    allow_redirects=True
)

print(f"   Логин: {response.status_code}")

if response.status_code == 200:
    print(f"   ✓ Логин успешен")
    
    # Проверяем доступ к TenantUser
    response = session.get('http://tenant1.localhost:8000/admin/users_app/tenantuser/')
    print(f"   Доступ к TenantUser: {response.status_code}")
    
    if response.status_code == 200:
        if 'admin_5' in response.text and 'worker_5' in response.text:
            print(f"   ✓ Видны пользователи Tenant 1 (admin_5, worker_5)")
        else:
            print(f"   ✗ Пользователи не видны")
    
    # Проверяем доступ к auth/user (должен быть запрещен)
    response = session.get('http://tenant1.localhost:8000/admin/auth/user/')
    print(f"   Доступ к auth/user: {response.status_code}")
    
    if response.status_code == 302:
        print(f"   ✓ Доступ запрещен (редирект на главную)")
    elif response.status_code == 200:
        if 'is_staff' in response.text:
            print(f"   ✗ Ошибка: is_staff attribute error")
        else:
            print(f"   ✓ Страница загружена без ошибок")
else:
    print(f"   ✗ Ошибка логина: {response.status_code}")

print("\n" + "=" * 70)
print("ТЕСТ ЗАВЕРШЕН")
print("=" * 70)
