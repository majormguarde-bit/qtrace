# Generated migration to add leads_to_stop field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('task_templates', '0010_add_parent_stage'),
    ]

    operations = [
        migrations.AddField(
            model_name='tasktemplatestage',
            name='leads_to_stop',
            field=models.BooleanField(default=False, verbose_name='Ведёт к финальному узлу (Stop)'),
        ),
    ]
