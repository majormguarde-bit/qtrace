#!/usr/bin/env python
"""
Тест отображения роли пользователя
"""
import requests
import json

print("Тест отображения роли пользователя\n")
print("=" * 60)

users = [
    ('admin_5', 'admin123'),
    ('worker_5', 'worker123'),
    ('admin_6', 'admin123'),
    ('worker_6', 'worker123'),
]

for username, password in users:
    response = requests.post(
        'http://localhost:8000/api/auth/token/',
        json={'username': username, 'password': password},
        headers={'Content-Type': 'application/json'},
        timeout=5
    )
    
    if response.status_code == 200:
        data = response.json()
        user = data.get('user', {})
        print(f"\n{username}:")
        print(f"  ID: {user.get('id')}")
        print(f"  Role: {user.get('role')}")
        print(f"  Full Response: {json.dumps(user, indent=2)}")
    else:
        print(f"\n{username}: FAILED ({response.status_code})")

print("\n" + "=" * 60)
