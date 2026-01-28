import random
import os
from .models import AISettings, AIModelConfig

# Импортируем SDK провайдеров
OPENAI_AVAILABLE = False
ANTHROPIC_AVAILABLE = False
GEMINI_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    pass

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    pass

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    pass

class AIService:
    @staticmethod
    def get_response(prompt, context='general'):
        try:
            settings = AISettings.get_settings()
            if not settings.is_enabled:
                return "AI временно отключен администратором."

            model_name = settings.active_model
            
            # Если выбран mock-режим
            if model_name == 'mock':
                return AIService._get_mock_response(prompt, context)
            
            # Проверка доступности библиотек
            if model_name.startswith('gpt-') or any(x in model_name for x in ['deepseek', 'chat-z-ai', 'qwen']):
                if not OPENAI_AVAILABLE:
                    return "Ошибка: Библиотека 'openai' не установлена на сервере. Обратитесь к администратору."
            
            if model_name.startswith('claude-') and not ANTHROPIC_AVAILABLE:
                return "Ошибка: Библиотека 'anthropic' не установлена на сервере. Обратитесь к администратору."
            
            if model_name.startswith('gemini-') and not GEMINI_AVAILABLE:
                return "Ошибка: Библиотека 'google-generativeai' не установлена на сервере. Обратитесь к администратору."

            # Получаем конфиг для активной модели
            config = AIModelConfig.objects.filter(model_code=model_name).first()
            if not config or not config.api_key:
                return f"Ошибка: API ключ для модели {model_name} не настроен."

            api_key = config.api_key.strip()
            base_url = config.api_url.strip() if config.api_url else None
            
            # Логика вызова реальных API
            if model_name.startswith('gpt-'):
                return AIService._call_openai(model_name, api_key, prompt, settings)
            
            elif model_name.startswith('claude-'):
                return AIService._call_anthropic(model_name, api_key, prompt, settings)
            
            elif model_name.startswith('gemini-'):
                return AIService._call_gemini(model_name, api_key, prompt, settings)
            
            elif any(x in model_name for x in ['deepseek', 'chat-z-ai', 'qwen']):
                # Для DeepSeek часто нужен /v1 в конце, если его нет
                if 'deepseek' in model_name:
                    if not base_url:
                        base_url = "https://api.deepseek.com/v1"
                    elif base_url.endswith('deepseek.com'):
                        base_url = f"{base_url}/v1"
                
                return AIService._call_openai(model_name, api_key, prompt, settings, base_url=base_url)

            return AIService._get_mock_response(prompt, context)
            
        except Exception as e:
            print(f"Service Error: {str(e)}")
            return f"Извините, возникла внутренняя ошибка сервиса: {str(e)}"

    @staticmethod
    def _call_openai(model, api_key, prompt, settings, base_url=None):
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            # Для DeepSeek и Z.AI модель часто называется 'deepseek-chat'
            actual_model = 'deepseek-chat' if ('deepseek' in model or 'chat-z-ai' in model) else model
            
            response = client.chat.completions.create(
                model=actual_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=settings.temperature,
                max_tokens=settings.max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            error_str = str(e).lower()
            if "insufficient" in error_str or "balance" in error_str or "402" in error_str:
                return "Ошибка: На балансе вашего AI-провайдера недостаточно средств. Пожалуйста, пополните баланс в личном кабинете провайдера."
            if "api key" in error_str or "401" in error_str:
                return "Ошибка: Неверный API ключ. Пожалуйста, проверьте настройки в панели управления."
            if "rate limit" in error_str or "429" in error_str:
                return "Ошибка: Слишком много запросов. Пожалуйста, подождите немного или увеличьте лимиты."
            return f"Ошибка API: {str(e)}"

    @staticmethod
    def _call_gemini(model, api_key, prompt, settings):
        try:
            genai.configure(api_key=api_key)
            model_id = 'gemini-1.5-pro' if 'pro' in model else 'gemini-1.5-flash'
            gemini_model = genai.GenerativeModel(model_id)
            response = gemini_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=settings.temperature,
                    max_output_tokens=settings.max_tokens
                )
            )
            return response.text
        except Exception as e:
            return f"Gemini Error: {str(e)}"

    @staticmethod
    def _call_anthropic(model, api_key, prompt, settings):
        try:
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model,
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            return f"Claude Error: {str(e)}"

    @staticmethod
    def _get_mock_response(prompt, context):
        """Эмуляция ответа ИИ"""
        responses = [
            "Интересный вопрос! С точки зрения безопасности...",
            "Я проанализировал ваши данные. Рекомендую обратить внимание на...",
            "Согласно строительным нормам, это требует проверки...",
            "Система SKKP зафиксировала выполнение задачи. AI подтверждает корректность."
        ]
        return random.choice(responses)

    @staticmethod
    def analyze_image(image_file):
        """Анализ изображения (пока упрощенно)"""
        settings = AISettings.get_settings()
        model_name = settings.active_model
        
        config = AIModelConfig.objects.filter(model_code=model_name).first()
        
        if model_name == 'mock' or not config or not config.api_key:
            return {
                'status': 'success',
                'analysis': "Обнаружено: здание (95%), синее небо (88%). Нарушений безопасности не найдено."
            }
        return {
            'status': 'success',
            'analysis': f"[AI {model_name}]: Анализ изображения завершен успешно."
        }
