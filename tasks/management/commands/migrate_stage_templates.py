from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context
from customers.models import Client
from tasks.models import TaskTemplateStage, Operation

class Command(BaseCommand):
    help = 'Migrate TaskTemplateStage data to Operation (Шаблоны этапов) for all tenants'

    def handle(self, *args, **options):
        # Получаем всех клиентов, кроме public
        clients = Client.objects.exclude(schema_name='public')
        
        total_created = 0
        
        for client in clients:
            self.stdout.write(f"Обработка тенанта: {client.name} ({client.schema_name})")
            with schema_context(client.schema_name):
                stages = TaskTemplateStage.objects.all()
                tenant_created = 0
                for stage in stages:
                    # Поле name в Operation уникально.
                    # Используем get_or_create, чтобы избежать дублей, если несколько шаблонов используют одинаковые названия этапов.
                    operation, created = Operation.objects.get_or_create(
                        name=stage.name,
                        defaults={
                            'executor_role': stage.executor_role,
                            'default_duration': stage.planned_duration,
                            'data_type': stage.data_type,
                            'description': f"Автоматически создано из шаблона: {stage.template.title}"
                        }
                    )
                    if created:
                        tenant_created += 1
                
                total_created += tenant_created
                self.stdout.write(self.style.SUCCESS(f"  Успешно создано {tenant_created} новых операций для {client.name}"))
        
        self.stdout.write(self.style.SUCCESS(f"Всего создано новых шаблонов этапов: {total_created}"))
