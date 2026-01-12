from django.core.management.base import BaseCommand
from django.db import connection
from customers.models import Client
from users_app.models import TenantUser

class Command(BaseCommand):
    help = 'Проверить пароль пользователя admin в тенанте abc'

    def handle(self, *args, **options):
        # Получаем тенанта abc
        client = Client.objects.get(schema_name='abc')
        connection.set_tenant(client)
        
        self.stdout.write(self.style.SUCCESS(f'=== Проверка паролей в тенанте: {client.name} ==='))
        
        # Список популярных паролей для проверки
        common_passwords = [
            'admin', 'admin123', 'password', '123456', '12345678', 'qwerty',
            'abc123', 'password123', 'admin1', 'root', 'test', 'demo',
            '12345', 'letmein', 'welcome', 'monkey', '1234567890'
        ]
        
        # Проверяем пользователя admin
        try:
            user = TenantUser.objects.get(username='admin')
            self.stdout.write(f'\nПользователь: {user.username} (роль: {user.role})')
            
            found_password = None
            # Проверяем стандартные пароли
            for password in common_passwords:
                if user.check_password(password):
                    found_password = password
                    break
            
            if found_password:
                self.stdout.write(self.style.SUCCESS(f'  ✅ Пароль найден: {found_password}'))
            else:
                self.stdout.write(self.style.WARNING('  ⚠️  Стандартный пароль не найден'))
                
                # Проверяем расширенный список
                extended_passwords = common_passwords + [
                    'admin', 'admin123', 'password', user.username, user.username + '123', 
                    user.username + '1', 'pass', 'pass123', '123', '0000', '1111'
                ]
                
                for password in extended_passwords:
                    if user.check_password(password):
                        self.stdout.write(self.style.SUCCESS(f'  ✅ НАЙДЕН ПАРОЛЬ: {password}'))
                        found_password = password
                        break
                
                if not found_password:
                    self.stdout.write(self.style.ERROR('  ❌ Пароль не найден в расширенном списке'))
                    
        except TenantUser.DoesNotExist:
            self.stdout.write(self.style.ERROR('Пользователь admin не найден'))
        
        # Показываем всех пользователей
        self.stdout.write('\n' + self.style.SUCCESS('='*50))
        self.stdout.write('Все пользователи тенанта:')
        users = TenantUser.objects.all()
        for user in users:
            status = "✅" if user.is_active else "❌"
            role_color = {
                'ADMIN': self.style.SUCCESS,
                'WORKER': self.style.HTTP_INFO,
                'MANAGER': self.style.WARNING,
            }.get(user.role, self.style.HTTP_NOT_MODIFIED)
            
            self.stdout.write(role_color(f'{status} {user.username:<15} | {user.role:<8} | {user.email:<25}'))