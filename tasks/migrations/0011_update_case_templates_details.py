from django.db import migrations

def update_case_templates(apps, schema_editor):
    TaskTemplate = apps.get_model('tasks', 'TaskTemplate')
    
    # Update Case 1: Auto Service
    auto = TaskTemplate.objects.filter(code='AUTO-TO-60').first()
    if auto:
        auto.description = 'Стандартизация сервисных операций для минимизации возвратов по гарантии.'
        auto.related_resource_name = 'Спецификация запчастей (масло, фильтры)'
        auto.related_resource_url = 'https://wiki.enterprise.com/auto/to-60-specs'
        auto.save()

    # Update Case 2: Microelectronics
    micro = TaskTemplate.objects.filter(code='QC-MICRO-02').first()
    if micro:
        micro.description = 'Мониторинг технологического процесса для предотвращения массового брака (AOI-анализ).'
        micro.related_resource_name = 'Технологическая карта изделия (Gerber-файлы)'
        micro.related_resource_url = 'https://wiki.enterprise.com/micro/qc-micro-02-gerber'
        micro.save()

def reverse_update(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('tasks', '0010_tasktemplate_related_resource_name_and_more'),
    ]

    operations = [
        migrations.RunPython(update_case_templates, reverse_update),
    ]
