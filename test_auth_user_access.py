#!/usr/bin/env python
"""
Тест доступа к auth/user через API (симуляция тенант-админа)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from customers.models import Client
from django_tenants.utils import tenant_context
from users_app.models import TenantUser

print("=" * 70)
print("ТЕСТ ДОСТУПА К AUTH/USER")
print("=" * 70)

# Проверяем, что admin_5 существует в Tenant 1
print("\n1. Проверка пользователей в Tenant 1")
client = Client.objects.get(schema_name='tenant_1')

with tenant_context(client):
    print(f"   Пользователи в {client.name}:")
    for user in TenantUser.objects.all():
        print(f"     - {user.username} ({user.get_role_display()})")
    
    # Проверяем, что auth.User не существует в tenant schema
    print(f"\n   Проверка auth.User в tenant schema:")
    try:
        users = User.objects.all()
        print(f"   ✗ Найдено {users.count()} пользователей auth.User (не должно быть!)")
        for user in users:
            print(f"     - {user.username}")
    except Exception as e:
        print(f"   ✓ Ошибка при доступе к auth.User: {str(e)[:100]}")

print("\n" + "=" * 70)
print("ТЕСТ ЗАВЕРШЕН")
print("=" * 70)
