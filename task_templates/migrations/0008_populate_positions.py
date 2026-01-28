# Generated migration to populate default positions

from django.db import migrations


def populate_positions(apps, schema_editor):
    Position = apps.get_model('task_templates', 'Position')
    
    positions = [
        {'name': 'Сварщик', 'description': 'Специалист по сварке'},
        {'name': 'Электрик', 'description': 'Специалист по электромонтажным работам'},
        {'name': 'Слесарь', 'description': 'Специалист по слесарным работам'},
        {'name': 'Монтажник', 'description': 'Специалист по монтажу оборудования'},
        {'name': 'Оператор', 'description': 'Оператор оборудования'},
        {'name': 'Инженер', 'description': 'Инженер-специалист'},
        {'name': 'Мастер', 'description': 'Мастер участка'},
        {'name': 'Технолог', 'description': 'Технолог производства'},
    ]
    
    for pos_data in positions:
        Position.objects.get_or_create(
            name=pos_data['name'],
            defaults={'description': pos_data['description'], 'is_active': True}
        )


def reverse_populate(apps, schema_editor):
    Position = apps.get_model('task_templates', 'Position')
    Position.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('task_templates', '0007_add_position_and_update_stages'),
    ]

    operations = [
        migrations.RunPython(populate_positions, reverse_populate),
    ]
