from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User


class ActivityCategory(models.Model):
    """Категория деятельности для классификации шаблонов"""
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    slug = models.SlugField(unique=True, verbose_name='Слаг')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлена')
    
    class Meta:
        db_table = 'activity_categories'
        ordering = ['name']
        verbose_name = 'Категория деятельности'
        verbose_name_plural = 'Категории деятельности'
    
    def __str__(self):
        return self.name


class UnitOfMeasure(models.Model):
    """Единица измерения для материалов"""
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True, verbose_name='Название')
    abbreviation = models.CharField(max_length=10, unique=True, verbose_name='Сокращение')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлена')
    
    class Meta:
        db_table = 'units_of_measure'
        ordering = ['name']
        verbose_name = 'Единица измерения'
        verbose_name_plural = 'Единицы измерения'
    
    def __str__(self):
        return f"{self.name} ({self.abbreviation})"


class Material(models.Model):
    """Материал или запчасть для использования в этапах"""
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    code = models.CharField(max_length=100, unique=True, verbose_name='Код материала')
    unit = models.ForeignKey(
        UnitOfMeasure,
        on_delete=models.PROTECT,
        verbose_name='Единица измерения'
    )
    
    # Стоимость для управленческого учета
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Стоимость за единицу'
    )
    
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    
    # Аудит
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлён')
    
    class Meta:
        db_table = 'materials'
        ordering = ['name']
        verbose_name = 'Материал'
        verbose_name_plural = 'Материалы'
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class DurationUnit(models.Model):
    """Единица времени для длительности этапов"""
    
    UNIT_CHOICES = [
        ('second', 'Секунда'),
        ('minute', 'Минута'),
        ('hour', 'Час'),
        ('day', 'День'),
        ('year', 'Год'),
    ]
    
    id = models.AutoField(primary_key=True)
    unit_type = models.CharField(max_length=10, choices=UNIT_CHOICES, unique=True, verbose_name='Тип')
    name = models.CharField(max_length=50, verbose_name='Название')
    abbreviation = models.CharField(max_length=5, verbose_name='Сокращение')
    
    class Meta:
        db_table = 'duration_units'
        ordering = ['id']
        verbose_name = 'Единица времени'
        verbose_name_plural = 'Единицы времени'
    
    def __str__(self):
        return f"{self.name} ({self.abbreviation})"


class Position(models.Model):
    """Должность для исполнителей этапов"""
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True, verbose_name='Название должности')
    description = models.TextField(blank=True, verbose_name='Описание')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлена')
    
    class Meta:
        db_table = 'positions'
        ordering = ['name']
        verbose_name = 'Должность'
        verbose_name_plural = 'Должности'
    
    def __str__(self):
        return self.name


class TaskTemplate(models.Model):
    """Шаблон задачи"""
    
    TEMPLATE_TYPE_CHOICES = [
        ('global', 'Глобальный'),
        ('local', 'Локальный'),
    ]
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    template_type = models.CharField(
        max_length=10, 
        choices=TEMPLATE_TYPE_CHOICES,
        default='global',
        verbose_name='Тип шаблона'
    )
    activity_category = models.ForeignKey(
        ActivityCategory,
        on_delete=models.PROTECT,
        related_name='templates',
        verbose_name='Категория деятельности'
    )
    
    # Для локальных шаблонов - ссылка на глобальный шаблон
    based_on_global = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='local_variants',
        verbose_name='Основан на глобальном'
    )
    
    # Версионирование
    version = models.IntegerField(default=1, verbose_name='Версия')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    
    # Аудит - используем User вместо TenantUser для public schema
    created_by_id = models.IntegerField(null=True, blank=True, verbose_name='Создан (ID)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_by_id = models.IntegerField(null=True, blank=True, verbose_name='Обновлён (ID)')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлён')
    
    class Meta:
        db_table = 'task_templates'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['template_type', 'is_active']),
            models.Index(fields=['activity_category', 'is_active']),
        ]
        verbose_name = 'Шаблон задачи'
        verbose_name_plural = 'Шаблоны задач'
    
    def __str__(self):
        return f"{self.name} (v{self.version})"


class TaskTemplateStage(models.Model):
    """Этап в шаблоне задачи"""
    
    id = models.AutoField(primary_key=True)
    template = models.ForeignKey(
        TaskTemplate,
        on_delete=models.CASCADE,
        related_name='stages',
        verbose_name='Шаблон'
    )
    name = models.CharField(max_length=255, verbose_name='Название')
    
    # Родительский этап (для иерархии)
    parent_stage = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_stages',
        verbose_name='Родительский этап'
    )
    
    # Длительность - диапазон (от и до) + единица времени
    duration_from = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Длительность от',
        default=1
    )
    duration_to = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Длительность до',
        default=1
    )
    duration_unit = models.ForeignKey(
        DurationUnit,
        on_delete=models.PROTECT,
        verbose_name='Единица времени',
        null=True,
        blank=True
    )
    
    # Должность исполнителя
    position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Должность'
    )
    
    # Порядок в шаблоне
    sequence_number = models.IntegerField(verbose_name='Номер последовательности')
    
    # Ведёт ли этап к финальному узлу (Stop)
    leads_to_stop = models.BooleanField(default=False, verbose_name='Ведёт к финальному узлу (Stop)')
    
    # Аудит
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлён')
    
    class Meta:
        db_table = 'task_template_stages'
        ordering = ['template', 'sequence_number']
        unique_together = [['template', 'sequence_number']]
        indexes = [
            models.Index(fields=['template', 'sequence_number']),
        ]
        verbose_name = 'Этап шаблона задачи'
        verbose_name_plural = 'Этапы шаблонов задач'
    
    def __str__(self):
        return f"{self.template.name} - {self.name}"




class StageMaterial(models.Model):
    """Материалы, используемые на этапе шаблона"""
    
    id = models.AutoField(primary_key=True)
    stage = models.ForeignKey(
        TaskTemplateStage,
        on_delete=models.CASCADE,
        related_name='materials',
        verbose_name='Этап'
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name='stage_usages',
        verbose_name='Материал'
    )
    
    # Количество материала, необходимое для этапа
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name='Количество'
    )
    
    # Аудит
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлён')
    
    class Meta:
        db_table = 'stage_materials'
        ordering = ['stage', 'material']
        unique_together = [['stage', 'material']]
        verbose_name = 'Материал этапа'
        verbose_name_plural = 'Материалы этапов'
    
    def __str__(self):
        return f"{self.stage.name} - {self.material.name} ({self.quantity} {self.material.unit.abbreviation})"
    
    @property
    def total_cost(self):
        """Общая стоимость материала для этапа"""
        return self.quantity * self.material.unit_cost


class TemplateProposal(models.Model):
    """Предложение шаблона для глобального репозитория"""
    
    STATUS_CHOICES = [
        ('pending', 'Ожидание'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    ]
    
    id = models.AutoField(primary_key=True)
    
    # Ссылка на локальный шаблон
    local_template = models.ForeignKey(
        TaskTemplate,
        on_delete=models.CASCADE,
        related_name='proposals',
        verbose_name='Локальный шаблон'
    )
    
    # Информация о предложителе (ID пользователя)
    proposed_by_id = models.IntegerField(null=True, blank=True, verbose_name='Предложено (ID)')
    
    # Статус
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )
    
    # Если одобрено - ссылка на созданный глобальный шаблон
    approved_global_template = models.ForeignKey(
        TaskTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_from_proposal',
        verbose_name='Одобренный глобальный шаблон'
    )
    
    # Если отклонено - причина
    rejection_reason = models.TextField(blank=True, verbose_name='Причина отклонения')
    
    # Аудит
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    reviewed_by_id = models.IntegerField(null=True, blank=True, verbose_name='Рассмотрено (ID)')
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата рассмотрения')
    
    class Meta:
        db_table = 'template_proposals'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['proposed_by_id', 'status']),
        ]
        verbose_name = 'Предложение шаблона'
        verbose_name_plural = 'Предложения шаблонов'
    
    def __str__(self):
        return f"Proposal: {self.local_template.name} ({self.status})"


class TemplateAuditLog(models.Model):
    """Журнал аудита операций с шаблонами"""
    
    ACTION_CHOICES = [
        ('create', 'Создание'),
        ('update', 'Обновление'),
        ('delete', 'Удаление'),
        ('approve_proposal', 'Одобрение предложения'),
        ('reject_proposal', 'Отклонение предложения'),
    ]
    
    id = models.AutoField(primary_key=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='Действие')
    
    # Объект, над которым выполнено действие
    template = models.ForeignKey(
        TaskTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name='Шаблон'
    )
    proposal = models.ForeignKey(
        TemplateProposal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name='Предложение'
    )
    
    # Пользователь, выполнивший действие (ID)
    performed_by_id = models.IntegerField(null=True, blank=True, verbose_name='Выполнено (ID)')
    
    # Детали изменения
    changes = models.JSONField(default=dict, verbose_name='Изменения')
    
    # Аудит
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    
    class Meta:
        db_table = 'template_audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['template', 'created_at']),
            models.Index(fields=['action', 'created_at']),
        ]
        verbose_name = 'Журнал аудита шаблонов'
        verbose_name_plural = 'Журналы аудита шаблонов'
    
    def __str__(self):
        return f"{self.action} - {self.created_at}"


class TemplateFilterPreference(models.Model):
    """Предпочтение фильтра шаблонов для пользователя"""
    
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(unique=True, verbose_name='Пользователь (ID)')
    
    # Показывать ли шаблоны из всех категорий
    show_all_categories = models.BooleanField(default=False, verbose_name='Показывать все категории')
    
    # Последний выбранный фильтр
    last_category_filter = models.ForeignKey(
        ActivityCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Последний фильтр категории'
    )
    
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    class Meta:
        db_table = 'template_filter_preferences'
        verbose_name = 'Предпочтение фильтра шаблонов'
        verbose_name_plural = 'Предпочтения фильтров шаблонов'
    
    def __str__(self):
        return f"Filter preference for user {self.user_id}"
