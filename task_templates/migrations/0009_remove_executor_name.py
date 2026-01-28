# Generated migration to remove executor_name field

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('task_templates', '0008_populate_positions'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tasktemplatestage',
            name='executor_name',
        ),
    ]
