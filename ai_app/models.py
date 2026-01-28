from django.db import models

class AIModelConfig(models.Model):
    """Настройки для конкретной модели ИИ"""
    model_code = models.CharField(max_length=50, unique=True, verbose_name="Код модели")
    api_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="API Ключ")
    api_url = models.URLField(max_length=255, blank=True, null=True, verbose_name="Base URL")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Конфигурация модели AI"
        verbose_name_plural = "Конфигурации моделей AI"

    def __str__(self):
        return self.model_code

class AISettings(models.Model):
    """Глобальные настройки AI"""
    MODEL_CHOICES = [
        ('mock', 'Эмуляция (без API)'),
        ('gpt-3.5-turbo', 'OpenAI GPT-3.5 Turbo'),
        ('gpt-4', 'OpenAI GPT-4'),
        ('gpt-4o', 'OpenAI GPT-4o (рекомендуется)'),
        ('claude-3-haiku-20240307', 'Anthropic Claude 3 Haiku'),
        ('claude-3-opus-20240229', 'Anthropic Claude 3 Opus'),
        ('gemini-1.5-pro', 'Google Gemini 1.5 Pro'),
        ('deepseek-v3.1', 'DeepSeek-V3.1 (Free)'),
        ('deepseek-3.2', 'DeepSeek-V3.2'),
        ('chat-z-ai', 'Z.AI (DeepSeek-V3)'),
        ('qwen-2.5', 'Alibaba Qwen-2.5'),
    ]

    active_model = models.CharField(max_length=50, choices=MODEL_CHOICES, default='mock', verbose_name="Активная модель")
    is_enabled = models.BooleanField(default=True, verbose_name="AI включен")
    temperature = models.FloatField(default=0.7, verbose_name="Температура")
    max_tokens = models.IntegerField(default=1000, verbose_name="Макс. токенов")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Настройки AI"
        verbose_name_plural = "Настройки AI"

    def __str__(self):
        return f"AI Settings: {self.get_active_model_display()}"

    @classmethod
    def get_settings(cls):
        settings, created = cls.objects.get_or_create(id=1)
        return settings
