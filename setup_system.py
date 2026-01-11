#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from customers.models import Client, Domain, SubscriptionPlan
from django.core.management import call_command

def setup():
    print("Настройка системы...")

    # 1. Создаем public tenant, если его нет
    public_tenant, created = Client.objects.get_or_create(
        schema_name='public',
        defaults={
            'name': 'Q-Trace Platform',
            'is_active': True,
        }
    )
    if created:
        print(f"✓ Создан основной тенант (public)")
    else:
        print(f"i Основной тенант уже существует")

    # 2. Создаем домен для public tenant
    # Для локальной разработки это localhost, для сервера нужно будет добавить ваш домен
    domain_name = 'localhost' # По умолчанию
    if not Domain.objects.filter(tenant=public_tenant).exists():
        Domain.objects.create(
            domain=domain_name,
            tenant=public_tenant,
            is_primary=True
        )
        print(f"✓ Домен {domain_name} привязан к public схеме")
    else:
        print(f"i Домен для public схемы уже настроен")

    # 3. Запускаем инициализацию тарифов
    print("Инициализация тарифных планов...")
    call_command('init_plans')
    
    plans_count = SubscriptionPlan.objects.count()
    print(f"\nГотово! В базе данных {plans_count} тарифов.")
    print("Теперь они должны появиться в админ-панели.")

if __name__ == "__main__":
    setup()
