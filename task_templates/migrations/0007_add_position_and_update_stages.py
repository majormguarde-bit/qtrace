# Generated migration

from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('task_templates', '0006_populate_duration_units'),
    ]

    operations = [
        # Create Position model
        migrations.CreateModel(
            name='Position',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255, unique=True, verbose_name='Название должности')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активна')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создана')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлена')),
            ],
            options={
                'verbose_name': 'Должность',
                'verbose_name_plural': 'Должности',
                'db_table': 'positions',
                'ordering': ['name'],
            },
        ),
        
        # Add new fields to TaskTemplateStage
        migrations.AddField(
            model_name='tasktemplatestage',
            name='duration_from',
            field=models.DecimalField(decimal_places=2, default=1, max_digits=10, validators=[django.core.validators.MinValueValidator(0.01)], verbose_name='Длительность от'),
        ),
        migrations.AddField(
            model_name='tasktemplatestage',
            name='duration_to',
            field=models.DecimalField(decimal_places=2, default=1, max_digits=10, validators=[django.core.validators.MinValueValidator(0.01)], verbose_name='Длительность до'),
        ),
        migrations.AddField(
            model_name='tasktemplatestage',
            name='executor_name',
            field=models.CharField(blank=True, max_length=255, verbose_name='Исполнитель'),
        ),
        migrations.AddField(
            model_name='tasktemplatestage',
            name='position',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='task_templates.position', verbose_name='Должность'),
        ),
        
        # Remove old fields
        migrations.RemoveField(
            model_name='tasktemplatestage',
            name='description',
        ),
        migrations.RemoveField(
            model_name='tasktemplatestage',
            name='estimated_duration',
        ),
    ]
