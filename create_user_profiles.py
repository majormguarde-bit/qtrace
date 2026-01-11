#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from customers.models import Client, UserProfile
from django_tenants.utils import schema_context

# Получить всех клиентов
clients = Client.objects.filter(schema_name__startswith='tenant_').order_by('id')

print(f"Создание профилей пользователей для {clients.count()} тенантов...\n")

for idx, client in enumerate(clients, 1):
    print(f"{'='*50}")
    print(f"Тенант {idx}: {client.name} (schema: {client.schema_name})")
    print(f"{'='*50}")
    
    with schema_context(client.schema_name):
        # Создать профиль для админа
        try:
            admin_user = User.objects.get(username=f'admin_{client.id}')
            profile, created = UserProfile.objects.get_or_create(
                user=admin_user,
                defaults={'role': 'ADMIN', 'tenant': client}
            )
            if created:
                print(f'✓ Профиль админа создан: {admin_user.username} (ADMIN)')
            else:
                profile.role = 'ADMIN'
                profile.tenant = client
                profile.save()
                print(f'✓ Профиль админа обновлен: {admin_user.username} (ADMIN)')
        except User.DoesNotExist:
            print(f'✗ Пользователь admin_{client.id} не найден')
        
        # Создать профиль для работника
        try:
            worker_user = User.objects.get(username=f'worker_{client.id}')
            profile, created = UserProfile.objects.get_or_create(
                user=worker_user,
                defaults={'role': 'WORKER', 'tenant': client}
            )
            if created:
                print(f'✓ Профиль работника создан: {worker_user.username} (WORKER)')
            else:
                profile.role = 'WORKER'
                profile.tenant = client
                profile.save()
                print(f'✓ Профиль работника обновлен: {worker_user.username} (WORKER)')
        except User.DoesNotExist:
            print(f'✗ Пользователь worker_{client.id} не найден')
        
        print(f'\nПользователи в {client.name}:')
        for user in User.objects.all():
            role = user.profile.get_role_display() if hasattr(user, 'profile') else "Нет профиля"
            print(f"- {user.username} (ID: {user.id}, Email: {user.email}, Роль: {role})")
    print("\n")
