from django.db import migrations

def create_case_templates(apps, schema_editor):
    TaskTemplate = apps.get_model('tasks', 'TaskTemplate')
    TaskTemplateStage = apps.get_model('tasks', 'TaskTemplateStage')

    # Case 1: Auto Service
    auto_template = TaskTemplate.objects.create(
        code='AUTO-TO-60',
        title='Регламентное техническое обслуживание (ТО-60)',
        description='Стандартизация сервисных операций для минимизации возвратов по гарантии. Спецификация запчастей: масло, фильтры.',
        process_type='CONTROL',
        category='Автосервис'
    )
    
    TaskTemplateStage.objects.create(
        template=auto_template,
        name='Входная диагностика и чек-лист',
        executor_role='INSPECTOR',
        planned_duration=20,
        data_type='LIST',
        order=1
    )
    TaskTemplateStage.objects.create(
        template=auto_template,
        name='Замена тех. жидкостей и фильтров',
        executor_role='WORKER',
        planned_duration=60,
        data_type='NUMBER',
        order=2
    )
    TaskTemplateStage.objects.create(
        template=auto_template,
        name='Проверка тормозной системы',
        executor_role='WORKER',
        planned_duration=30,
        data_type='NUMBER',
        order=3
    )
    TaskTemplateStage.objects.create(
        template=auto_template,
        name='Сброс сервисного интервала (ЭБУ)',
        executor_role='WORKER',
        planned_duration=15,
        data_type='CHECKBOX',
        order=4
    )
    TaskTemplateStage.objects.create(
        template=auto_template,
        name='Выходной контроль ОТК',
        executor_role='INSPECTOR',
        planned_duration=15,
        data_type='NUMBER',
        order=5
    )

    # Case 2: Microelectronics
    micro_template = TaskTemplate.objects.create(
        code='QC-MICRO-02',
        title='Контроль качества пайки SMT-линии',
        description='Мониторинг технологического процесса для предотвращения массового брака (AOI-анализ). Связанный ресурс: Технологическая карта изделия (Gerber-файлы).',
        process_type='CONTROL',
        category='Микроэлектроника'
    )
    
    TaskTemplateStage.objects.create(
        template=micro_template,
        name='Нанесение паяльной пасты (SPI)',
        executor_role='WORKER',
        planned_duration=5,
        data_type='NUMBER',
        order=1
    )
    TaskTemplateStage.objects.create(
        template=micro_template,
        name='Установка компонентов (Pick & Place)',
        executor_role='WORKER',
        planned_duration=10,
        data_type='NUMBER',
        order=2
    )
    TaskTemplateStage.objects.create(
        template=micro_template,
        name='Групповое оплавление (Reflow)',
        executor_role='WORKER',
        planned_duration=20,
        data_type='NUMBER',
        order=3
    )
    TaskTemplateStage.objects.create(
        template=micro_template,
        name='Автоматическая оптика (AOI)',
        executor_role='INSPECTOR',
        planned_duration=10,
        data_type='NUMBER',
        order=4
    )
    TaskTemplateStage.objects.create(
        template=micro_template,
        name='Рентген-контроль (X-Ray)',
        executor_role='INSPECTOR',
        planned_duration=15,
        data_type='NUMBER',
        order=5
    )

def remove_case_templates(apps, schema_editor):
    TaskTemplate = apps.get_model('tasks', 'TaskTemplate')
    TaskTemplate.objects.filter(code__in=['AUTO-TO-60', 'QC-MICRO-02']).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('tasks', '0007_tasktemplate_alter_task_source_task_template_and_more'),
    ]

    operations = [
        migrations.RunPython(create_case_templates, remove_case_templates),
    ]
