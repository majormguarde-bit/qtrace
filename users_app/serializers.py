from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from .models import TenantUser


class TenantUserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователя тенанта"""
    
    class Meta:
        model = TenantUser
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role')
        read_only_fields = ('id',)


class DjangoUserSerializer(serializers.ModelSerializer):
    """Сериализатор для Django User"""
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id',)


class CustomTokenObtainPairSerializer(serializers.Serializer):
    """Кастомный сериализатор для получения токена с данными пользователя"""
    
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        from django.contrib.auth import authenticate
        
        username = attrs.get('username')
        password = attrs.get('password')
        
        # Аутентифицировать пользователя
        user = authenticate(username=username, password=password)
        
        if not user:
            raise serializers.ValidationError('No active account found with the given credentials')
        
        # Получить токены
        refresh = RefreshToken()
        refresh['user_id'] = user.id
        refresh['username'] = user.username
        
        if isinstance(user, TenantUser):
            refresh['user_type'] = 'tenant'
        else:
            refresh['user_type'] = 'public'
        
        # Выбрать правильный сериализатор в зависимости от типа пользователя
        if isinstance(user, TenantUser):
            user_serializer = TenantUserSerializer(user)
        else:
            user_serializer = DjangoUserSerializer(user)
        
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': user_serializer.data
        }
        
        return data
