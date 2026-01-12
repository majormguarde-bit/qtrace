from django.core import signing
from django.core.signing import BadSignature, SignatureExpired
from .models import TenantUser
from django.contrib.auth import get_user_model

def generate_quick_login_token(user):
    """
    Генерирует подписанный URL-safe токен для быстрого входа.
    Токен содержит ID пользователя и хеш пароля (для инвалидации при смене пароля).
    """
    if isinstance(user, TenantUser):
        data = {
            'type': 'tenant',
            'id': user.id,
            'hash': user.password_hash
        }
    else:
        data = {
            'type': 'system',
            'id': user.id,
            'hash': user.password
        }
        
    # Используем signing.dumps для создания URL-safe строки (base64url)
    return signing.dumps(data, salt='quick_login')

def validate_quick_login_token(token, max_age=31536000): # 1 год по умолчанию
    """
    Проверяет токен и возвращает пользователя.
    """
    try:
        # Декодируем и проверяем подпись
        data = signing.loads(token, salt='quick_login', max_age=max_age)
        
        user_type = data.get('type')
        user_id = data.get('id')
        password_hash = data.get('hash')
        
        if not all([user_type, user_id, password_hash]):
            return None
        
        if user_type == 'tenant':
            try:
                user = TenantUser.objects.get(pk=user_id)
                if user.password_hash != password_hash:
                    return None
                return user
            except TenantUser.DoesNotExist:
                return None
        elif user_type == 'system':
            User = get_user_model()
            try:
                user = User.objects.get(pk=user_id)
                if user.password != password_hash:
                    return None
                return user
            except User.DoesNotExist:
                return None
                
        return None
        
    except (BadSignature, SignatureExpired, ValueError, TypeError):
        return None
