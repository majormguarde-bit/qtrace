from django.core.management.base import BaseCommand
from django.db import connection
from customers.models import Client
from users_app.models import TenantUser

class Command(BaseCommand):
    help = 'Показать всех пользователей тенанта abc с их ролями'

    def handle(self, *args, **options):
        # Получаем тенанта abc
        client = Client.objects.get(schema_name='abc')
        connection.set_tenant(client)
        
        self.stdout.write(self.style.SUCCESS(f'=== Тенант: {client.name} ==='))
        
        # Показываем всех пользователей с деталями
        users = TenantUser.objects.all().order_by('role', 'username')
        
        if users.exists():
            self.stdout.write('\nВсе пользователи:')
            for user in users:
                status = "✓" if user.is_active else "✗"
                role_color = {
                    'ADMIN': self.style.SUCCESS,
                    'WORKER': self.style.HTTP_INFO,
                    'MANAGER': self.style.WARNING,
                }.get(user.role, self.style.HTTP_NOT_MODIFIED)
                
                self.stdout.write(role_color(f'{status} {user.username:<15} | {user.role:<8} | {user.email:<25} | Активен: {user.is_active}'))
            
            # Показываем администраторов отдельно
            admins = TenantUser.objects.filter(role='ADMIN', is_active=True)
            if admins.exists():
                self.stdout.write(self.style.SUCCESS('\n🎯 Активные администраторы:'))
                for admin in admins:
                    self.stdout.write(self.style.SUCCESS(f'   ➤ {admin.username} ({admin.email})'))
            else:
                self.stdout.write(self.style.WARNING('\n⚠️  Активные администраторы не найдены!'))
                
        else:
            self.stdout.write(self.style.ERROR('❌ Пользователи не найдены!'))