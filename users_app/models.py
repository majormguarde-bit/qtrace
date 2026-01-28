from django.db import models
from django.contrib.auth.models import User


class Department(models.Model):
    """Подразделение тенанта (иерархическая структура)"""
    name = models.CharField(max_length=255, verbose_name='Название')
    parent = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='children',
        verbose_name='Головное подразделение'
    )
    description = models.TextField(blank=True, verbose_name='Описание')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Подразделение'
        verbose_name_plural = 'Подразделения'
        ordering = ['name']

    def __str__(self):
        if self.parent:
            return f"{self.parent} -> {self.name}"
        return self.name

    def get_full_path(self):
        """Возвращает полную цепочку подразделения"""
        parts = [self.name]
        p = self.parent
        while p:
            parts.insert(0, p.name)
            p = p.parent
        return " / ".join(parts)


class Position(models.Model):
    """Должность сотрудника"""
    name = models.CharField(max_length=255, unique=True, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Должность'
        verbose_name_plural = 'Должности'
        ordering = ['name']

    def __str__(self):
        return self.name


class TenantUser(models.Model):
    """Пользователь тенанта (локальная копия для каждого тенанта)"""
    
    ROLE_CHOICES = [
        ('ADMIN', 'Администратор'),
        ('WORKER', 'Работник'),
    ]
    
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField()
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='Должность'
    )
    department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='users',
        verbose_name='Подразделение'
    )
    password_hash = models.CharField(max_length=255)  # Возвращаем исходное имя
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='WORKER'
    )
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Пользователь тенанта'
        verbose_name_plural = 'Пользователи тенанта'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def set_password(self, raw_password):
        """Установить пароль"""
        from django.contrib.auth.hashers import make_password
        self.password_hash = make_password(raw_password)
    
    def check_password(self, raw_password):
        """Проверить пароль"""
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password_hash)
    
    def get_username(self):
        """Получить имя пользователя"""
        return self.username
    
    def get_full_name(self):
        """Получить полное имя пользователя"""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.username
    
    def get_short_name(self):
        """Получить короткое имя пользователя"""
        return self.first_name or self.username
    
    @property
    def is_authenticated(self):
        """Всегда True для экземпляров TenantUser"""
        return True

    @property
    def is_anonymous(self):
        """Всегда False для экземпляров TenantUser"""
        return False

    @property
    def is_staff(self):
        """Проверить, является ли пользователь администратором"""
        return self.role == 'ADMIN' and self.is_active
    
    @property
    def is_superuser(self):
        """
        Администратор тенанта НЕ является суперпользователем всей платформы.
        Возвращаем False, чтобы избежать случайного доступа к системным настройкам.
        """
        return False
    
    def has_perm(self, perm, obj=None):
        """Проверить, есть ли у пользователя разрешение"""
        if self.role == 'ADMIN' and self.is_active:
            return True
        return False
    
    def has_module_perms(self, app_label):
        """Проверить, есть ли у пользователя разрешения на модуль"""
        if self.role == 'ADMIN' and self.is_active:
            return True
        return False


# Для обратной совместимости
User = User

