# Migration to ensure auth.User exists in public schema

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0003_add_schema_name'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
    ]
