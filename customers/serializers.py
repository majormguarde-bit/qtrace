from rest_framework import serializers
from customers.models import Client

class TenantRegistrationSerializer(serializers.Serializer):
    """
    Сериализатор для регистрации нового тенанта (предприятия).
    """
    company_name = serializers.CharField(max_length=100)
    subdomain = serializers.CharField(max_length=63)
    admin_username = serializers.CharField(max_length=150)
    admin_email = serializers.EmailField()
    admin_password = serializers.CharField(write_only=True)
    phone = serializers.CharField(max_length=20)
    telegram = serializers.CharField(max_length=100, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    contact_person = serializers.CharField(max_length=255, required=False, allow_blank=True)
    subscription_plan = serializers.IntegerField(required=True)
    
    def validate_subdomain(self, value):
        if Client.objects.filter(schema_name=value).exists():
            raise serializers.ValidationError("Subdomain already exists.")
        if value in ['public', 'www', 'admin']:
            raise serializers.ValidationError("Invalid subdomain.")
        return value
