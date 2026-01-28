#!/usr/bin/env python
"""
Создание пользователей тенанта (TenantUser) для каждого тенанта.
Каждый тенант имеет своих админов и работников.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from customers.models import Client
from django_tenants.utils import tenant_context
from users_app.models import TenantUser

# Получить всех клиентов
clients = Client.objects.filter(schema_name__startswith='tenant_').order_by('id')

print(f"Создание пользователей тенанта для {clients.count()} тенантов...\n")

for idx, client in enumerate(clients, 1):
    print(f"{'='*50}")
    print(f"Тенант {idx}: {client.name} (schema: {client.schema_name})")
    print(f"{'='*50}")
    
    with tenant_context(client):
        # Создать админа
        admin_user, created = TenantUser.objects.get_or_create(
            username=f'admin_{client.id}',
            defaults={
                'email': f'admin_{client.id}@example.com',
                'first_name': 'Admin',
                'last_name': f'Tenant {client.id}',
                'role': 'ADMIN',
                'is_active': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            print(f'✓ Админ создан: {admin_user.username} (ADMIN)')
        else:
            print(f'✓ Админ уже существует: {admin_user.username} (ADMIN)')
        
        # Создать работника
        worker_user, created = TenantUser.objects.get_or_create(
            username=f'worker_{client.id}',
            defaults={
                'email': f'worker_{client.id}@example.com',
                'first_name': 'Worker',
                'last_name': f'Tenant {client.id}',
                'role': 'WORKER',
                'is_active': True,
            }
        )
        if created:
            worker_user.set_password('worker123')
            worker_user.save()
            print(f'✓ Работник создан: {worker_user.username} (WORKER)')
        else:
            print(f'✓ Работник уже существует: {worker_user.username} (WORKER)')
        
        print(f'\nПользователи в {client.name}:')
        for user in TenantUser.objects.all():
            print(f'  - {user.username} ({user.get_role_display()})')
        print()

print(f"{'='*50}")
print("✓ Создание пользователей завершено")
