#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from customers.models import Client
from django_tenants.utils import schema_context

# Получаем тенантов
tenants = Client.objects.all()
print(f"Найдено тенантов: {tenants.count()}")

for tenant in tenants:
    print(f"\nТенант: {tenant.name} (schema: {tenant.schema_name})")
    
    # Переходим в контекст тенанта
    with schema_context(tenant.schema_name):
        # Проверяем пользователей в этом тенанте
        users = User.objects.all()
        print(f"  Пользователей в тенанте: {users.count()}")
        for user in users:
            print(f"    - {user.username}")
            
        # Если нет админа, создаем
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_user(
                username='admin',
                email='admin@example.com',
                password='admin123',
                is_staff=True,
                is_superuser=False
            )
            print(f"  ✓ Создан пользователь: admin")
        else:
            admin_user = User.objects.get(username='admin')
            print(f"  ✓ Пользователь admin уже существует")

print("\n✅ Готово!")
