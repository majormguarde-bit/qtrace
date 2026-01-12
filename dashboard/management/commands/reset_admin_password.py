from django.core.management.base import BaseCommand
from django.db import connection
from customers.models import Client
from users_app.models import TenantUser

class Command(BaseCommand):
    help = 'Сбросить пароль пользователя admin в тенанте abc'

    def add_arguments(self, parser):
        parser.add_argument('password', type=str, help='Новый пароль')

    def handle(self, *args, **options):
        password = options['password']
        
        # Получаем тенанта abc
        client = Client.objects.get(schema_name='abc')
        connection.set_tenant(client)
        
        try:
            user = TenantUser.objects.get(username='admin')
            user.set_password(password)
            user.save()
            
            self.stdout.write(self.style.SUCCESS(f'✅ Пароль для пользователя admin успешно изменен на: {password}'))
            self.stdout.write(self.style.SUCCESS('Теперь вы можете войти в систему используя admin/' + password))
            
        except TenantUser.DoesNotExist:
            self.stdout.write(self.style.ERROR('❌ Пользователь admin не найден в тенанте abc'))