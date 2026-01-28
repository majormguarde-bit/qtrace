#!/usr/bin/env python
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django_tenants.utils import get_tenant_model

# Удаляем миграции из public schema
with connection.cursor() as cursor:
    cursor.execute("DELETE FROM django_migrations WHERE app = 'task_templates'")
    print('Миграции task_templates удалены из public schema')

# Удаляем миграции из всех tenant schemas
Tenant = get_tenant_model()
for tenant in Tenant.objects.all():
    tenant.activate()
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM django_migrations WHERE app = 'task_templates'")
        print(f'Миграции task_templates удалены из schema {tenant.schema_name}')
