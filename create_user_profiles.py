#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from customers.models import Client
from django_tenants.utils import tenant_context
from users_app.models import UserProfile

# Получить всех клиентов
clients = Client.objects.filter(schema_name__startswith='tenant_').order_by('id')

print(f"Создание профилей пользователей для {clients.count()} тенантов...\n")

for idx, client in enumerate(clients, 1):
    print(f"{'='*50}")
    print(f"Тенант {idx}: {client.name} (schema: {client.schema_name})")
    print(f"{'='*50}")
    
    with tenant_context(client):
        # Создать профиль для админа
        admin_user = User.objects.get(username=f'admin_{client.id}')
        profile, created = UserProfile.objects.get_or_create(
            user=admin_user,
            defaults={'role': 'ADMIN'}
        )
        if created:
            print(f'✓ Профиль админа создан: {admin_user.username} (ADMIN)')
        else:
            profile.role = 'ADMIN'
            profile.save()
            print(f'✓ Профиль админа обновлен: {admin_user.username} (ADMIN)')
        
        # Создать профиль для работника
        worker_user = User.objects.get(username=f'worker_{client.id}')
        profile, created = UserProfile.objects.get_or_create(
            user=worker_user,
            defaults={'role': 'WORKER'}
        )
        if created:
            print(f'✓ Профиль работника создан: {worker_user.username} (WORKER)')
        else:
            profile.role = 'WORKER'
            profile.save()
            print(f'✓ Профиль работника обновлен: {worker_user.username} (WORKER)')
        
        print(f'\nПользователи в {client.name}:')
        for user in User.objects.all():
            try:
                role = user.profile.get_role_display()
            except:
                role = 'N/A'
            print(f'  - {user.username} ({role})')
        print()

print(f"{'='*50}")
print("✓ Создание профилей завершено")
