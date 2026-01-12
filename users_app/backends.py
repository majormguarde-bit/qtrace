from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db import connection
from .models import TenantUser


class TenantUserBackend(ModelBackend):
    """
    Backend для аутентификации пользователей тенанта (TenantUser).
    Используется ТОЛЬКО для tenant schemas.
    Также автоматически создает TenantUser для суперпользователей Django.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """Аутентифицировать пользователя TenantUser или суперпользователя Django"""
        # Если мы в публичной схеме, этот бэкенд не должен работать
        if connection.tenant.schema_name == 'public':
            return None
            
        # Сначала пробуем найти существующего TenantUser
        try:
            tenant_user = TenantUser.objects.get(username=username)
            if tenant_user.check_password(password) and tenant_user.is_active:
                return tenant_user
        except TenantUser.DoesNotExist:
            pass
        
        # Если TenantUser не найден, проверяем суперпользователя Django
        try:
            django_user = User.objects.get(username=username)
            if django_user.is_superuser and django_user.check_password(password) and django_user.is_active:
                # Создаем или обновляем TenantUser для суперпользователя
                tenant_user, created = TenantUser.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': django_user.email,
                        'first_name': django_user.first_name,
                        'last_name': django_user.last_name,
                        'role': 'ADMIN',  # Суперпользователь всегда администратор
                        'is_active': True,
                    }
                )
                
                # Если TenantUser существует, обновляем данные
                if not created:
                    tenant_user.email = django_user.email
                    tenant_user.first_name = django_user.first_name
                    tenant_user.last_name = django_user.last_name
                    tenant_user.role = 'ADMIN'  # Убеждаемся, что роль ADMIN
                    tenant_user.is_active = True
                    tenant_user.save()
                
                # Устанавливаем пароль
                tenant_user.set_password(password)
                tenant_user.save()
                
                return tenant_user
                
        except User.DoesNotExist:
            return None
    
    def get_user(self, user_id):
        """Получить пользователя TenantUser по ID"""
        # Если мы в публичной схеме, этот бэкенд не должен работать
        if connection.tenant.schema_name == 'public':
            return None
            
        try:
            return TenantUser.objects.get(pk=user_id)
        except TenantUser.DoesNotExist:
            return None

