import os
import django
import sys

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django.contrib.auth import get_user_model

def reset_admin():
    # Ensure we are on public schema
    connection.set_schema_to_public()
    print("Switched to public schema.", flush=True)

    User = get_user_model()
    username = 'admin'
    password = 'admin'
    email = 'admin@example.com'

    try:
        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            user.set_password(password)
            user.is_superuser = True
            user.is_staff = True
            user.is_active = True
            user.save()
            print(f"Successfully updated existing user '{username}'. Password reset to '{password}'.", flush=True)
        else:
            User.objects.create_superuser(username=username, email=email, password=password)
            print(f"Successfully created new superuser '{username}' with password '{password}'.", flush=True)
    except Exception as e:
        print(f"An error occurred: {e}", flush=True)

if __name__ == "__main__":
    reset_admin()
