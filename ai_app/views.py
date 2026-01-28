from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .services import AIService

@csrf_exempt
def ai_chat_api(request):
    if request.method == 'POST':
        try:
            # Пытаемся получить данные из JSON тела запроса
            try:
                data = json.loads(request.body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Если не получилось, пробуем из POST параметров (на всякий случай)
                data = request.POST
            
            prompt = data.get('prompt', '')
            context = data.get('context', 'general')
            
            if not prompt:
                return JsonResponse({'status': 'error', 'message': 'Пустой запрос'}, status=400)

            response_text = AIService.get_response(prompt, context=context)
            
            return JsonResponse({
                'status': 'success',
                'response': response_text
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f"Ошибка сервера: {str(e)}"
            }, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Метод не разрешен'}, status=405)

@csrf_exempt
def ai_analyze_photo(request):
    if request.method == 'POST':
        # В реальной системе здесь будет обработка файла
        analysis = AIService.analyze_image(None)
        return JsonResponse(analysis)
    return JsonResponse({'status': 'error'}, status=405)
