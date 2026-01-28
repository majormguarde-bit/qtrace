from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from django.contrib.auth import get_user_model
from .models import TenantUser

class TenantJWTAuthentication(JWTAuthentication):
    """
    Кастомная JWT аутентификация, поддерживающая TenantUser.
    Проверяет claim 'user_type' в токене.
    """
    
    def get_user(self, validated_token):
        """
        Attempt to find and return a user using the given validated token.
        """
        try:
            user_id = validated_token['user_id']
            user_type = validated_token.get('user_type', 'public')
        except KeyError:
            raise InvalidToken('Token contained no recognizable user identification')

        if user_type == 'tenant':
            try:
                user = TenantUser.objects.get(id=user_id)
            except TenantUser.DoesNotExist:
                raise AuthenticationFailed('User not found', code='user_not_found')
        else:
            # Public user (standard Django User)
            try:
                user = get_user_model().objects.get(id=user_id)
            except get_user_model().DoesNotExist:
                raise AuthenticationFailed('User not found', code='user_not_found')

        if not user.is_active:
            raise AuthenticationFailed('User is inactive', code='user_inactive')

        return user
