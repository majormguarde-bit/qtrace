#!/usr/bin/env python
import requests
import json

BASE_URL = "http://localhost:8000"

print("=== Тестирование API авторизации с изоляцией тенантов ===\n")

# Тест 1: Логин админа Tenant 1
print("1️⃣ Логин админа Tenant 1:")
response = requests.post(
    f"{BASE_URL}/api/auth/token/",
    json={
        "username": "admin_5",
        "password": "admin123"
    },
    headers={"Host": "tenant1.localhost"}
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"✓ Токен получен: {data['access'][:20]}...")
    print(f"✓ Пользователь: {data['user']['username']} ({data['user']['role']})")
    tenant1_token = data['access']
else:
    print(f"✗ Ошибка: {response.text}")
    tenant1_token = None

# Тест 2: Логин работника Tenant 1
print("\n2️⃣ Логин работника Tenant 1:")
response = requests.post(
    f"{BASE_URL}/api/auth/token/",
    json={
        "username": "worker_5",
        "password": "worker123"
    },
    headers={"Host": "tenant1.localhost"}
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"✓ Токен получен: {data['access'][:20]}...")
    print(f"✓ Пользователь: {data['user']['username']} ({data['user']['role']})")
else:
    print(f"✗ Ошибка: {response.text}")

# Тест 3: Логин админа Tenant 2
print("\n3️⃣ Логин админа Tenant 2:")
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
    tenant2_token = data['access']
else:
    print(f"✗ Ошибка: {response.text}")
    tenant2_token = None

# Тест 4: Логин работника Tenant 2
print("\n4️⃣ Логин работника Tenant 2:")
response = requests.post(
    f"{BASE_URL}/api/auth/token/",
    json={
        "username": "worker_6",
        "password": "worker123"
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

# Тест 5: Проверка изоляции - админ Tenant 1 не может логиниться как админ Tenant 2
print("\n5️⃣ Проверка изоляции - админ Tenant 1 не может логиниться в Tenant 2:")
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
    print(f"✓ Ошибка 401 - пользователь не найден в Tenant 2 (изоляция работает)")
else:
    print(f"✗ Ожидалась ошибка 401, получена {response.status_code}")

# Тест 6: Получить данные текущего пользователя (Tenant 1)
if tenant1_token:
    print("\n6️⃣ Получить данные админа Tenant 1:")
    response = requests.get(
        f"{BASE_URL}/api/users/me/",
        headers={
            "Authorization": f"Bearer {tenant1_token}",
            "Host": "tenant1.localhost"
        }
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Данные пользователя:")
        print(f"  - Username: {data['username']}")
        print(f"  - Role: {data['role']}")
    else:
        print(f"✗ Ошибка: {response.text}")

print("\n=== Тестирование завершено ===")
print("\n📋 Учетные данные:")
print("Tenant 1:")
print("  - Админ: admin_5 / admin123")
print("  - Работник: worker_5 / worker123")
print("Tenant 2:")
print("  - Админ: admin_6 / admin123")
print("  - Работник: worker_6 / worker123")
