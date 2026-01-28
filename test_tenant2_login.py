#!/usr/bin/env python
import requests
import json

BASE_URL = "http://localhost:8000"

print("=== Тестирование логина admin_6 в Tenant 2 ===\n")

# Тест 1: Логин через localhost (должен быть Tenant 1)
print("1️⃣ Логин admin_6 через localhost (Tenant 1):")
response = requests.post(
    f"{BASE_URL}/api/auth/token/",
    json={
        "username": "admin_6",
        "password": "admin123"
    }
)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}\n")

# Тест 2: Логин через tenant2.localhost
print("2️⃣ Логин admin_6 через tenant2.localhost (Tenant 2):")
response = requests.post(
    f"{BASE_URL}/api/auth/token/",
    json={
        "username": "admin_6",
        "password": "admin123"
    },
    headers={"Host": "tenant2.localhost"}
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"✓ Токен получен: {data['access'][:20]}...")
    print(f"✓ Пользователь: {data['user']['username']} ({data['user']['role']})")
else:
    print(f"✗ Ошибка: {response.text}")

# Тест 3: Логин admin_5 через tenant2.localhost (должен быть 401)
print("\n3️⃣ Логин admin_5 через tenant2.localhost (должен быть 401):")
response = requests.post(
    f"{BASE_URL}/api/auth/token/",
    json={
        "username": "admin_5",
        "password": "admin123"
    },
    headers={"Host": "tenant2.localhost"}
)
print(f"Status: {response.status_code}")
if response.status_code == 401:
    print(f"✓ Ошибка 401 как ожидается")
else:
    print(f"✗ Ожидалась 401, получена {response.status_code}")
