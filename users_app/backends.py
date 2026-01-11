from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db import connection
from .models import TenantUser


class TenantUserBackend(ModelBackend):
    """
    Backend для аутентификации пользователей тенанта (TenantUser).
    Используется ТОЛЬКО для tenant schemas.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """Аутентифицировать пользователя TenantUser"""
        # Если мы в публичной схеме, этот бэкенд не должен работать
        if connection.tenant.schema_name == 'public':
            return None
            
        try:
            user = TenantUser.objects.get(username=username)
            if user.check_password(password) and user.is_active:
                return user
        except TenantUser.DoesNotExist:
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

