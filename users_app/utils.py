from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from .models import TenantUser
from django.contrib.auth import get_user_model

def generate_quick_login_token(user):
    """
    Генерирует подписанный токен для быстрого входа.
    Токен содержит ID пользователя и хеш пароля (для инвалидации при смене пароля).
    """
    signer = TimestampSigner(salt='quick_login')
    # Если это TenantUser
    if isinstance(user, TenantUser):
        value = f"tenant:{user.id}:{user.password_hash}"
    else:
        # Если это системный User
        value = f"system:{user.id}:{user.password}"
        
    return signer.sign(value)

def validate_quick_login_token(token, max_age=31536000): # 1 год по умолчанию
    """
    Проверяет токен и возвращает пользователя.
    """
    signer = TimestampSigner(salt='quick_login')
    try:
        value = signer.unsign(token, max_age=max_age)
        parts = value.split(':', 2)
        
        if len(parts) != 3:
            return None
            
        user_type, user_id, password_hash = parts
        
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
        
    except (BadSignature, SignatureExpired):
        return None
