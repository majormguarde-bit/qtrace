from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class AdminPasswordLog(models.Model):
    """Модель для логирования генерации паролей администратором"""
    
    ACTION_CHOICES = [
        ('generated', 'Сгенерирован'),
        ('reset', 'Сброшен'),
        ('viewed', 'Просмотрен'),
        ('deleted', 'Удален'),
    ]
    
    admin_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Администратор (Django User)')
    admin_username = models.CharField(max_length=150, default='unknown', verbose_name='Имя администратора')
    employee_username = models.CharField(max_length=150, verbose_name='Логин сотрудника')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default='generated', verbose_name='Действие')
    password_length = models.IntegerField(default=16, verbose_name='Длина пароля')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP адрес')
    user_agent = models.TextField(blank=True, verbose_name='User Agent')
    notes = models.TextField(blank=True, verbose_name='Примечания')
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Лог генерации пароля'
        verbose_name_plural = 'Логи генерации паролей'
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['employee_username']),
            models.Index(fields=['admin_user']),
            models.Index(fields=['admin_username']),
        ]
    
    def __str__(self):
        admin_name = self.admin_user.username if self.admin_user else self.admin_username
        return f"{admin_name} - {self.employee_username} ({self.get_action_display()}) - {self.timestamp}"
