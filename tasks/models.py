from django.db import models

from users_app.models import TenantUser


class Task(models.Model):
    """Модель задачи для тенанта"""
    STATUS_CHOICES = [
        ('OPEN', 'Открыта'),
        ('PAUSE', 'Пауза'),
        ('CONTINUE', 'Продолжить'),
        ('IMPORTANT', 'Важно'),
        ('CLOSE', 'Закрыть задачу'),
    ]

    title = models.CharField(max_length=200, verbose_name='Заголовок')
    description = models.TextField(blank=True, verbose_name='Описание')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN', verbose_name='Статус')
    is_completed = models.BooleanField(default=False, verbose_name='Завершена')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class TaskStage(models.Model):
    """Этап выполнения задачи"""
    STAGE_STATUS_CHOICES = [
        ('PENDING', 'В планах'),
        ('IN_PROGRESS', 'В работе'),
        ('COMPLETED', 'Завершен'),
        ('FAILED', 'Проблема'),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='stages', verbose_name='Задача')
    name = models.CharField(max_length=200, verbose_name='Название этапа')
    duration_minutes = models.PositiveIntegerField(default=0, verbose_name='Длительность (мин)')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    is_completed = models.BooleanField(default=False, verbose_name='Завершен')
    status = models.CharField(max_length=20, choices=STAGE_STATUS_CHOICES, default='PENDING', verbose_name='Статус этапа')
    is_worker_added = models.BooleanField(default=False, verbose_name='Добавлено сотрудником')
    
    # Исполнитель этапа
    assigned_to = models.ForeignKey(TenantUser, on_delete=models.SET_NULL, related_name='stage_assignments', null=True, blank=True, verbose_name='Исполнитель')
    
    # Новые поля для наследования из шаблона
    position_id = models.IntegerField(blank=True, null=True, verbose_name='ID должности (из public schema)')
    position_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='Название должности')
    duration_text = models.CharField(max_length=100, blank=True, null=True, verbose_name='Длительность (текст)')
    materials_info = models.JSONField(default=list, blank=True, verbose_name='Информация о материалах')

    class Meta:
        verbose_name = 'Этап задачи'
        verbose_name_plural = 'Этапы задачи'
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.task.title} - {self.name}"

