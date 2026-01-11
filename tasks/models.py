from django.db import models
from users_app.models import TenantUser


class TaskTemplate(models.Model):
    """Шаблон задачи для справочной системы предприятия"""
    PROCESS_TYPE_CHOICES = [
        ('AUDIT', 'Аудит'),
        ('CONTROL', 'Контроль партии'),
        ('INSPECTION', 'Инспекция'),
        ('REVIEW', 'Ревью'),
        ('PRODUCTION', 'Заказ на производство'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name='Код шаблона', help_text='Напр. QC-MICRO-02')
    title = models.CharField(max_length=200, verbose_name='Название процесса')
    description = models.TextField(blank=True, verbose_name='Описание / Инструкция (Wiki)')
    process_type = models.CharField(max_length=20, choices=PROCESS_TYPE_CHOICES, default='CONTROL', verbose_name='Тип процесса')
    category = models.CharField(max_length=100, blank=True, verbose_name='Категория (напр. Автосервис, Электроника)')
    
    # Ссылка на внешние ресурсы (Wiki, Gerber, Спецификации)
    related_resource_url = models.URLField(blank=True, verbose_name='Ссылка на ресурс (Wiki/Docs)')
    related_resource_name = models.CharField(max_length=100, blank=True, verbose_name='Название ресурса')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Шаблон задачи'
        verbose_name_plural = 'Справочник процессов (Шаблоны)'

    def __str__(self):
        return f"[{self.code}] {self.title}"

class TaskTemplateStage(models.Model):
    """Этап в шаблоне задачи"""
    ROLE_CHOICES = [
        ('ADMIN', 'Администратор'),
        ('WORKER', 'Работник'),
        ('LAB_TECH', 'Лаборант'),
        ('INSPECTOR', 'Инспектор'),
    ]

    template = models.ForeignKey(TaskTemplate, on_delete=models.CASCADE, related_name='stages', verbose_name='Шаблон')
    name = models.CharField(max_length=200, verbose_name='Название этапа')
    executor_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='WORKER', verbose_name='Роль исполнителя')
    planned_duration = models.PositiveIntegerField(default=0, verbose_name='Норматив SLA (мин)')
    
    # Дополнительные поля для интерактивных форм
    data_type = models.CharField(max_length=50, choices=[
        ('TEXT', 'Текст / Описание'),
        ('NUMBER', 'Числовое значение'),
        ('CHECKBOX', 'Pass / Fail (Чек-бокс)'),
        ('MEDIA', 'Медиаотчет (Фото/Видео)'),
        ('LIST', 'Список неисправностей'),
    ], default='TEXT', verbose_name='Тип данных для аналитики')
    
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name = 'Этап шаблона'
        verbose_name_plural = 'Этапы шаблона'
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.template.code} - {self.name}"

class Product(models.Model):
    """Справочник изделий"""
    name = models.CharField(max_length=255, verbose_name='Наименование')
    article = models.CharField(max_length=100, unique=True, verbose_name='Артикул')
    description = models.TextField(blank=True, verbose_name='Описание')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Изделие'
        verbose_name_plural = 'Справочник изделий'

    def __str__(self):
        return f"{self.article} | {self.name}"

class Specification(models.Model):
    """Справочник спецификаций (BOM)"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='specifications', verbose_name='Изделие')
    code = models.CharField(max_length=100, verbose_name='Код спецификации')
    version = models.CharField(max_length=50, blank=True, verbose_name='Версия')
    file_url = models.URLField(blank=True, verbose_name='Ссылка на файлы')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Спецификация'
        verbose_name_plural = 'Справочник спецификаций'

    def __str__(self):
        return f"{self.code} (v{self.version}) - {self.product.name}"

class TransferNote(models.Model):
    """Справочник накладных на перемещение"""
    number = models.CharField(max_length=100, unique=True, verbose_name='Номер накладной')
    date = models.DateField(verbose_name='Дата накладной')
    description = models.TextField(blank=True, verbose_name='Комментарий')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Накладная'
        verbose_name_plural = 'Справочник накладных'

    def __str__(self):
        return f"№{self.number} от {self.date}"

class Operation(models.Model):
    """Справочник этапов / операций (Шаблоны этапов)"""
    ROLE_CHOICES = [
        ('ADMIN', 'Администратор'),
        ('WORKER', 'Работник'),
        ('LAB_TECH', 'Лаборант'),
        ('INSPECTOR', 'Инспектор'),
    ]

    DATA_TYPE_CHOICES = [
        ('TEXT', 'Текст / Описание'),
        ('NUMBER', 'Числовое значение'),
        ('CHECKBOX', 'Pass / Fail (Чек-бокс)'),
        ('MEDIA', 'Медиаотчет (Фото/Видео)'),
        ('LIST', 'Список неисправностей'),
    ]

    name = models.CharField(max_length=255, unique=True, verbose_name='Название операции')
    description = models.TextField(blank=True, verbose_name='Описание операции')
    default_duration = models.PositiveIntegerField(default=0, verbose_name='Норматив SLA (мин)')
    executor_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='WORKER', verbose_name='Роль исполнителя')
    data_type = models.CharField(max_length=50, choices=DATA_TYPE_CHOICES, default='TEXT', verbose_name='Тип данных')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Шаблон этапа'
        verbose_name_plural = 'Шаблоны этапов'

    def __str__(self):
        return self.name

class ClientOrder(models.Model):
    """Справочник заказов (внешних)"""
    order_number = models.CharField(max_length=100, unique=True, verbose_name='Номер заказа')
    client_name = models.CharField(max_length=255, verbose_name='Заказчик')
    date = models.DateField(verbose_name='Дата заказа')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Справочник заказов'

    def __str__(self):
        return f"Заказ {self.order_number} ({self.client_name})"

class Task(models.Model):
    """Модель задачи для тенанта в соответствии с ТЗ для аналитики"""
    STATUS_CHOICES = [
        ('OPEN', 'Открыта'),
        ('PAUSE', 'Пауза'),
        ('CONTINUE', 'В работе'),
        ('IMPORTANT', 'Важно'),
        ('CLOSE', 'Закрыта'),
    ]

    PROCESS_TYPE_CHOICES = TaskTemplate.PROCESS_TYPE_CHOICES

    PRIORITY_CHOICES = [
        (1, 'Низкий'),
        (2, 'Нормальный'),
        (3, 'Срочный'),
        (4, 'Горит'),
    ]

    SOURCE_CHOICES = [
        ('PLANNED', 'Плановая проверка'),
        ('COMPLAINT', 'Жалоба клиента'),
        ('FAILURE', 'Сбой на линии'),
        ('TEMPLATE', 'Из справочника (шаблон)'),
    ]

    external_id = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name='ID заказа', help_text='Напр. PRD-2024-00123')
    template = models.ForeignKey(TaskTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks', verbose_name='Шаблон процесса')
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    description = models.TextField(blank=True, verbose_name='Особые отметки / Описание')
    
    # Раздел 1: Шапка
    deadline = models.DateField(null=True, blank=True, verbose_name='Плановая дата выпуска')
    client_name = models.CharField(max_length=200, blank=True, verbose_name='Заказчик (Клиент)')
    manager = models.ForeignKey(TenantUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_tasks', verbose_name='Ответственный менеджер')
    
    # Раздел 2: Информация об изделии
    product_name = models.CharField(max_length=200, blank=True, verbose_name='Наименование изделия')
    article_number = models.CharField(max_length=100, blank=True, verbose_name='Артикул / Децимальный номер')
    pcb_revision = models.CharField(max_length=50, blank=True, verbose_name='Ревизия (Версия) PCB')
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество к производству (шт.)')
    panel_type = models.CharField(max_length=100, blank=True, verbose_name='Вид панели', help_text='Одиночная или мультиблок')
    
    # Раздел 3: Техническая документация
    bom_id = models.CharField(max_length=100, blank=True, verbose_name='ID Спецификации (BOM)')
    project_files_url = models.URLField(blank=True, verbose_name='Файлы проекта (Gerber, P&P)')
    firmware_version = models.CharField(max_length=50, blank=True, verbose_name='Версия прошивки')
    stencil_id = models.CharField(max_length=100, blank=True, verbose_name='ID Трафарета')
    
    # Раздел 4: Статус комплектации
    transfer_note_number = models.CharField(max_length=100, blank=True, verbose_name='Накладная на перемещение')
    kit_status = models.CharField(max_length=20, choices=[('FULL', 'Полная'), ('PARTIAL', 'Частичная')], default='FULL', verbose_name='Статус комплектации')
    deficit_list = models.TextField(blank=True, verbose_name='Список дефицита')
    kit_received_date = models.DateField(null=True, blank=True, verbose_name='Дата получения комплектующих')
    
    # Раздел 6: Контроль качества
    quality_defects = models.TextField(blank=True, verbose_name='Выявленные дефекты')
    repair_quantity = models.PositiveIntegerField(default=0, verbose_name='Количество на ремонт')
    scrap_quantity = models.PositiveIntegerField(default=0, verbose_name='Количество брака (Scrap)')
    
    # Раздел 7: Итоговые данные
    actual_produced_quantity = models.PositiveIntegerField(default=0, verbose_name='Фактически произведено (шт.)')
    leftover_components = models.TextField(blank=True, verbose_name='Остатки компонентов')
    finished_goods_date = models.DateField(null=True, blank=True, verbose_name='Дата сдачи на склад ГП')
    production_manager_signed = models.BooleanField(default=False, verbose_name='Подпись Начальника производства')
    production_manager_signed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата подписи')

    process_type = models.CharField(max_length=20, choices=PROCESS_TYPE_CHOICES, default='CONTROL', verbose_name='Тип процесса')
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=3, verbose_name='Приоритет')
    control_object = models.CharField(max_length=100, blank=True, verbose_name='Объект контроля', help_text='ID продукта, документа или сотрудника')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='PLANNED', verbose_name='Источник задачи')
    
    assigned_to = models.ForeignKey(TenantUser, on_delete=models.CASCADE, related_name='tasks', null=True, blank=True, verbose_name='Исполнитель')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN', verbose_name='Статус')
    is_completed = models.BooleanField(default=False, verbose_name='Завершена')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата закрытия')

    class Meta:
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.external_id}] {self.title}"

    @property
    def total_damage(self):
        """Сумма ущерба по всем этапам задачи"""
        return self.stages.aggregate(total=models.Sum('damage_amount'))['total'] or 0

    @property
    def lead_time(self):
        """Общее время: от создания до закрытия (в минутах)"""
        if self.closed_at:
            delta = self.closed_at - self.created_at
            return int(delta.total_seconds() / 60)
        return None

    @property
    def cycle_time(self):
        """Время цикла: сумма фактической длительности всех этапов (в минутах)"""
        return self.stages.aggregate(total=models.Sum('actual_duration'))['total'] or 0

    @property
    def wait_time(self):
        """Время ожидания: Lead Time - Cycle Time"""
        lt = self.lead_time
        if lt is not None:
            return lt - self.cycle_time
        return None

    @property
    def efficiency_score(self):
        """Коэффициент эффективности: (Plan_Duration / Fact_Duration) * 100"""
        plan = self.stages.aggregate(total=models.Sum('planned_duration'))['total'] or 0
        fact = self.cycle_time
        if fact > 0:
            return int((plan / fact) * 100)
        return 0

    @property
    def quality_score(self):
        """Процент успешных этапов (без брака)"""
        total = self.stages.count()
        if total > 0:
            success = self.stages.filter(result_status=True).count()
            return int((success / total) * 100)
        return 100

class TaskStage(models.Model):
    """Этап выполнения задачи с расширенной аналитикой"""
    STAGE_STATUS_CHOICES = [
        ('PENDING', 'В планах'),
        ('IN_PROGRESS', 'В работе'),
        ('COMPLETED', 'Завершен'),
        ('FAILED', 'Проблема'),
    ]

    REASON_CODE_CHOICES = [
        ('NONE', 'Нет'),
        ('TEMP_ERR', 'Нарушение температурного режима'),
        ('TYPO', 'Опечатка'),
        ('BAD_PIXEL', 'Битый пиксель'),
        ('MATERIAL_DEFECT', 'Дефект материала'),
        ('HUMAN_FACTOR', 'Человеческий фактор'),
    ]

    CRITICALITY_CHOICES = [
        ('MINOR', 'Малозначимый'),
        ('SIGNIFICANT', 'Значимый'),
        ('CRITICAL', 'Критический'),
    ]

    ROLE_CHOICES = TaskTemplateStage.ROLE_CHOICES

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='stages', verbose_name='Задача')
    name = models.CharField(max_length=200, verbose_name='Название этапа')
    executor_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='WORKER', verbose_name='Роль исполнителя')
    assigned_executor = models.ForeignKey(TenantUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_stages', verbose_name='Назначенный сотрудник')
    equipment = models.CharField(max_length=100, blank=True, verbose_name='Рабочее место (Оборудование)')
    
    planned_duration = models.PositiveIntegerField(default=0, verbose_name='План. длит. (мин)')
    actual_duration = models.PositiveIntegerField(default=0, verbose_name='Факт. длит. (мин)')
    
    start_timestamp = models.DateTimeField(null=True, blank=True, verbose_name='Время начала')
    end_timestamp = models.DateTimeField(null=True, blank=True, verbose_name='Время окончания')
    
    status = models.CharField(max_length=20, choices=STAGE_STATUS_CHOICES, default='PENDING', verbose_name='Статус этапа')
    result_status = models.BooleanField(default=True, verbose_name='Результат (успех/брак)')
    
    quantity_good = models.PositiveIntegerField(default=0, verbose_name='Кол-во (Годных)')
    reason_code = models.CharField(max_length=20, choices=REASON_CODE_CHOICES, default='NONE', verbose_name='Код отклонения')
    defect_criticality = models.CharField(max_length=20, choices=CRITICALITY_CHOICES, default='MINOR', verbose_name='Критичность дефекта')
    damage_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Сумма ущерба')
    
    is_completed = models.BooleanField(default=False, verbose_name='Завершен')
    is_worker_added = models.BooleanField(default=False, verbose_name='Добавлено сотрудником')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    
    # Поля для структурированных данных из шаблонов
    data_type = models.CharField(max_length=50, choices=[
        ('TEXT', 'Текст / Описание'),
        ('NUMBER', 'Числовое значение'),
        ('CHECKBOX', 'Pass / Fail (Чек-бокс)'),
        ('MEDIA', 'Медиаотчет (Фото/Видео)'),
        ('LIST', 'Список неисправностей'),
    ], default='TEXT', verbose_name='Тип данных для аналитики')
    data_value = models.TextField(blank=True, verbose_name='Значение данных', help_text='Результат этапа (число, текст или JSON)')

    class Meta:
        verbose_name = 'Этап задачи'
        verbose_name_plural = 'Этапы задачи'
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.task.external_id} - {self.name}"

    def save(self, *args, **kwargs):
        # Логика аналитических триггеров
        if self.pk: # Только для существующих (обновляемых) этапов
            old_stage = TaskStage.objects.get(pk=self.pk)
            if old_stage.data_value != self.data_value:
                self.check_analytical_triggers()
        
        super().save(*args, **kwargs)

    def check_analytical_triggers(self):
        """Проверка условий для автоматического создания задач или алертов"""
        # Кейс: Автосервис - Износ тормозных колодок > 80%
        if "тормозной системы" in self.name.lower() and self.data_type == 'NUMBER':
            try:
                value = float(self.data_value)
                if value > 80:
                    # Создаем дочернюю задачу
                    Task.objects.get_or_create(
                        title=f"Согласование замены колодок ({self.task.external_id})",
                        defaults={
                            'description': f"Автоматическая задача: выявлен критический износ {value}% на этапе {self.name}.",
                            'priority': 4,
                            'process_type': 'AUDIT',
                            'source': 'FAILURE',
                            'status': 'OPEN'
                        }
                    )
            except (ValueError, TypeError):
                pass

        # Кейс: Электроника - Брак AOI > 2%
        if "aoi" in self.name.lower() and self.data_type == 'NUMBER':
            try:
                value = float(self.data_value)
                if value > 2:
                    Task.objects.get_or_create(
                        title=f"Корректировка параметров трафаретной печати ({self.task.external_id})",
                        defaults={
                            'description': f"Критический уровень брака AOI: {value}%. Требуется остановка линии и проверка параметров.",
                            'priority': 5,
                            'process_type': 'CONTROL',
                            'source': 'FAILURE',
                            'status': 'IMPORTANT'
                        }
                    )
            except (ValueError, TypeError):
                pass

