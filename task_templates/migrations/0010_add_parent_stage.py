# Generated migration to add parent_stage field

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('task_templates', '0009_remove_executor_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='tasktemplatestage',
            name='parent_stage',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='child_stages', to='task_templates.tasktemplatestage', verbose_name='Родительский этап'),
        ),
    ]
