# Generated migration to populate DurationUnit table

from django.db import migrations


def populate_duration_units(apps, schema_editor):
    """Предзаполняем таблицу DurationUnit"""
    DurationUnit = apps.get_model('task_templates', 'DurationUnit')
    
    units_data = [
        {'unit_type': 'second', 'name': 'Секунда', 'abbreviation': 'сек'},
        {'unit_type': 'minute', 'name': 'Минута', 'abbreviation': 'мин'},
        {'unit_type': 'hour', 'name': 'Час', 'abbreviation': 'ч'},
        {'unit_type': 'day', 'name': 'День', 'abbreviation': 'д'},
        {'unit_type': 'year', 'name': 'Год', 'abbreviation': 'г'},
    ]
    
    for unit_data in units_data:
        DurationUnit.objects.create(**unit_data)


def reverse_populate(apps, schema_editor):
    """Удаляем предзаполненные данные при откате"""
    DurationUnit = apps.get_model('task_templates', 'DurationUnit')
    DurationUnit.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('task_templates', '0005_alter_durationunit_unit_type'),
    ]

    operations = [
        migrations.RunPython(populate_duration_units, reverse_populate),
    ]
