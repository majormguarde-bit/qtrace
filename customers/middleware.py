from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone

class TenantStatusMiddleware:
    """
    Middleware для проверки активности тенанта (is_active) и срока подписки.
    Если тенант заблокирован или подписка истекла, доступ закрыт.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # request.tenant устанавливается TenantMainMiddleware, который идет ПЕРЕД этим middleware
        tenant = getattr(request, 'tenant', None)
        
        # Если это публичная схема (администраторская панель), обновляем сессию
        if tenant and tenant.schema_name == 'public':
            # Обновляем время жизни сессии для администраторов
            if hasattr(request, 'user') and request.user.is_authenticated:
                request.session.modified = True
        
        # Если это не публичная схема
        if tenant and tenant.schema_name != 'public':
            # Проверка флага активности
            if not getattr(tenant, 'is_active', True):
                return render(request, 'customers/tenant_locked.html', {
                    'tenant': tenant,
                    'reason': 'Ваша организация ожидает активации администратором или временно заблокирована.'
                }, status=403)
            
            # Проверка срока подписки
            if getattr(tenant, 'subscription_end_date', None) and tenant.subscription_end_date < timezone.now().date():
                return HttpResponseForbidden(
                    f"<h1>Срок подписки истек</h1><p>Срок действия вашей подписки истек ({tenant.subscription_end_date}). Пожалуйста, продлите доступ.</p>"
                )

        response = self.get_response(request)
        return response
