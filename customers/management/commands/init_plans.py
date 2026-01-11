from django.core.management.base import BaseCommand
from customers.models import SubscriptionPlan

class Command(BaseCommand):
    help = 'Инициализирует стандартные тарифные планы в публичной схеме'

    def handle(self, *args, **options):
        plans = [
            {
                'name': 'Ознакомительный',
                'price_month': 0,
                'max_users': 10,
                'storage_gb': 10,
                'work_days_limit': 15,
                'has_mobile_app': True,
                'description': 'Бесплатный тестовый период для ознакомления с возможностями системы.'
            },
            {
                'name': 'Лайт',
                'price_month': 25000,
                'max_users': 10,
                'storage_gb': 100,
                'work_days_limit': 30,
                'has_mobile_app': True,
                'description': 'Оптимальное решение для небольших команд и стартапов.'
            },
            {
                'name': 'Базовый',
                'price_month': 60000,
                'max_users': 25,
                'storage_gb': 100,
                'work_days_limit': 30,
                'has_mobile_app': True,
                'description': 'Расширенные возможности для растущего бизнеса.'
            },
            {
                'name': 'Профи',
                'price_month': 150000,
                'max_users': 100,
                'storage_gb': 10000,
                'work_days_limit': 30,
                'has_mobile_app': True,
                'description': 'Полный функционал для крупных предприятий с высокими требованиями.'
            },
            {
                'name': 'Договорной',
                'price_month': 0,
                'max_users': 999999,
                'storage_gb': 1000000,
                'work_days_limit': 30,
                'has_mobile_app': True,
                'description': 'Индивидуальные условия для специальных проектов и корпораций.'
            },
        ]

        created_count = 0
        updated_count = 0

        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.update_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Создан тариф: {plan.name}"))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f"Обновлен тариф: {plan.name}"))

        self.stdout.write(self.style.SUCCESS(
            f"Итого: создано {created_count}, обновлено {updated_count}"
        ))
