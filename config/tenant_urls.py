from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
import os
from users_app.admin import tenant_aware_admin_site
from dashboard import views as dashboard_views
from config.error_handlers import custom_page_not_found, custom_server_error

handler404 = custom_page_not_found
handler500 = custom_server_error

def tenant_media_serve(request, path, **kwargs):
    """Специальный обработчик для медиа-файлов тенанта в режиме разработки"""
    document_root = os.path.join(settings.MEDIA_ROOT, request.tenant.schema_name)
    return serve(request, path, document_root=document_root, **kwargs)

from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', tenant_aware_admin_site.urls),
    path('api/', include('users_app.urls')),
    path('api/', include('tasks.urls')),
    path('api/', include('media_app.urls')),
    path('ai/', include('ai_app.urls')),
    
    # Auth routes
    path('login/', dashboard_views.TenantLoginView.as_view(), name='login'),
    path('logout/', dashboard_views.TenantLogoutView.as_view(), name='logout'),
    
    # Dashboard routes
    path('dashboard/', include('dashboard.urls')),
    path('', RedirectView.as_view(pattern_name='dashboard:home', permanent=False)),
]

if settings.DEBUG:
    urlpatterns += [
        path('media/<path:path>', tenant_media_serve),
    ]
