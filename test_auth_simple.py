#!/usr/bin/env python
"""
Простой тест аутентификации через localhost
"""
import requests
import json

BASE_URL = 'http://localhost:8000'

print("Тестирование аутентификации\n")
print("=" * 60)

# Тест 1: Логин admin_5
print("\nТест 1: Логин admin_5")
response = requests.post(
    f"{BASE_URL}/api/auth/token/",
    json={
        'username': 'admin_5',
        'password': 'admin123',
    },
    headers={'Content-Type': 'application/json'},
    timeout=5
)

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 200:
    data = response.json()
    print(f"✓ Успех!")
    print(f"  Access Token: {data.get('access', '')[:50]}...")
    print(f"  User: {data.get('user')}")
else:
    print(f"✗ Ошибка")

print("\n" + "=" * 60)
