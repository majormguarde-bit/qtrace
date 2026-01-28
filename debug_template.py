
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import RequestFactory
from django.template import Template, Context
from django_tenants.utils import schema_context
from customers.models import Client
from users_app.models import TenantUser

# Setup
client = Client.objects.exclude(schema_name='public').first()
if not client:
    print("No tenant found")
    exit()

print(f"Tenant: {client.schema_name}")

with schema_context(client.schema_name):
    try:
        user = TenantUser.objects.get(username='admin_5')
    except TenantUser.DoesNotExist:
        print("User admin_5 not found")
        exit()
        
    print(f"User: {user} (Role: {user.role})")
    
    # Template simulation
    template_string = """
    {% if user.role == 'ADMIN' %}
        Result: Администратор
    {% elif user.role == 'WORKER' %}
        Result: Сотрудник
    {% else %}
        Result: {{ user.get_role_display|default:"Сотрудник" }}
    {% endif %}
    
    Direct Role: '{{ user.role }}'
    Direct Display: '{{ user.get_role_display }}'
    """
    
    t = Template(template_string)
    c = Context({'user': user})
    rendered = t.render(c)
    print("--- Rendered Template ---")
    print(rendered)
