from django.db import models
from django.contrib.auth.models import User
from django_tenants.models import TenantMixin, DomainMixin
from django.db.models import Sum
from django.utils import timezone

class Client(TenantMixin):
    name = models.CharField(max_length=100)
    created_on = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=False)
    phone = models.CharField(max_length=20, blank=True, null=True)
    telegram = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    subscription_plan = models.ForeignKey('SubscriptionPlan', on_delete=models.SET_NULL, null=True, blank=True)
    subscription_end_date = models.DateField(null=True, blank=True)
    can_admin_delete_media = models.BooleanField(default=False, verbose_name='Разрешить админу удалять медиа')

    auto_create_schema = True
    auto_drop_schema = True

    def __str__(self):
        return self.name

class Domain(DomainMixin):
    pass

class UserProfile(models.Model):
    """Профиль пользователя с ролью для public schema (системные пользователи)"""
    
    ROLE_CHOICES = [
        ('ADMIN', 'Администратор'),
        ('WORKER', 'Работник'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    tenant = models.ForeignKey('Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='user_profiles')
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='WORKER'
    )
    can_delete_media = models.BooleanField(default=False, verbose_name='Разрешить удаление файлов')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    price_month = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_year = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_users = models.IntegerField(default=10)
    storage_gb = models.IntegerField(default=5)
    work_days_limit = models.IntegerField(default=30)
    has_mobile_app = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.price_month} руб/мес)"

class Payment(models.Model):
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date = models.DateField(default=timezone.now, null=True, blank=True)
    description = models.CharField(max_length=255, default='', blank=True, null=True)
    
    def __str__(self):
        return f"{self.tenant.name if self.tenant else 'Unknown'} - {self.amount} - {self.date}"

class MailSettings(models.Model):
    email_host = models.CharField(max_length=255, default='', blank=True, null=True)
    email_port = models.IntegerField(default=587)
    email_host_user = models.CharField(max_length=255, default='', blank=True, null=True)
    email_host_password = models.CharField(max_length=255, default='', blank=True, null=True)
    email_use_tls = models.BooleanField(default=True)
    email_use_ssl = models.BooleanField(default=False)
    default_from_email = models.EmailField(default='', blank=True, null=True)

    class Meta:
        verbose_name = "Настройки почты"
        verbose_name_plural = "Настройки почты"

    @classmethod
    def get_settings(cls):
        settings, created = cls.objects.get_or_create(id=1)
        return settings

    def __str__(self):
        return f"SMTP: {self.email_host}"

class ContactMessage(models.Model):
    name = models.CharField(max_length=100, default='', blank=True, null=True)
    email = models.EmailField(default='', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    subject = models.CharField(max_length=200, default='', blank=True, null=True)
    message = models.TextField(default='', blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, default='', blank=True, null=True)
    is_sent = models.BooleanField(default=False)
    error_log = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.email}"
