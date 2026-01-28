from django.db import models
from users_app.models import TenantUser


from tasks.models import Task, TaskStage
import os
from django.utils import timezone

def get_media_upload_path(instance, filename):
    """
    Формирует путь и имя файла: кто_что_когда.расширение
    """
    who = "unknown"
    if instance.uploaded_by:
        who = instance.uploaded_by.get_full_name() or instance.uploaded_by.username
    
    what = "media"
    if instance.stage:
        what = instance.stage.name
    elif instance.task:
        what = instance.task.title
        
    when = timezone.now().strftime("%Y%m%d_%H%M%S")
    
    # Очистка имени от спецсимволов для файловой системы
    import re
    def slugify(value):
        value = re.sub(r'[^\w\s-]', '', value).strip().lower()
        return re.sub(r'[-\s]+', '_', value)

    ext = os.path.splitext(filename)[1]
    new_filename = f"{slugify(who)}_{slugify(what)}_{when}{ext}"
    
    return os.path.join('tenant_media/', new_filename)

class Media(models.Model):
    """Модель медиа-файла для тенанта"""
    title = models.CharField(max_length=200, verbose_name='Название', blank=True)
    file = models.FileField(upload_to=get_media_upload_path, verbose_name='Файл')
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, related_name='media', null=True, blank=True, verbose_name='Задача')
    stage = models.ForeignKey(TaskStage, on_delete=models.SET_NULL, related_name='media', null=True, blank=True, verbose_name='Этап')
    uploaded_by = models.ForeignKey(TenantUser, on_delete=models.CASCADE, related_name='media', null=True, blank=True, verbose_name='Загрузил')
    
    # Поля для мобильного приложения
    recording_start = models.DateTimeField(null=True, blank=True, verbose_name='Начало съемки')
    recording_end = models.DateTimeField(null=True, blank=True, verbose_name='Конец съемки')
    
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата загрузки')

    class Meta:
        verbose_name = 'Медиа-файл'
        verbose_name_plural = 'Медиа-файлы'
        ordering = ['-uploaded_at']

    def save(self, *args, **kwargs):
        if not self.title and self.file:
            who = "unknown"
            if self.uploaded_by:
                who = self.uploaded_by.get_full_name() or self.uploaded_by.username
            
            what = "media"
            if self.stage:
                what = self.stage.name
            elif self.task:
                what = self.task.title
                
            when = timezone.now().strftime("%d.%m.%Y %H:%M")
            self.title = f"{who} - {what} ({when})"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
