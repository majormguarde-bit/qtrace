from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
import os
from customers.views import (
    landing_page, superuser_dashboard, superuser_tenants, 
    superuser_tenant_edit, superuser_tenant_toggle_status,
    superuser_tenant_delete,
    superuser_domains, superuser_domain_create, superuser_domain_edit,
    superuser_domain_delete,
    superuser_admins, superuser_admin_edit,
    superuser_admin_create, superuser_admin_delete,
    superuser_tenant_admin_edit, superuser_tenant_admin_delete,
    superuser_plans, superuser_plan_create, superuser_plan_edit,
    superuser_plan_delete,
    superuser_finance, superuser_client_payments, superuser_payment_add,
    superuser_payment_edit, superuser_payment_delete,
    superuser_mail_settings, contact_form_submit,
    superuser_mail_logs, get_captcha, superuser_mail_log_delete,
    superuser_mail_log_edit, superuser_ai_settings,
    superuser_db_management, superuser_db_cleanup_tenants,
    superuser_db_vacuum, superuser_db_backup, superuser_db_restore,
    public_tariffs, TenantRegistrationViewSet, SuperuserLoginView
)
from dashboard import views as dashboard_views
from config.error_handlers import custom_page_not_found, custom_server_error

handler404 = custom_page_not_found
handler500 = custom_server_error

def universal_media_serve(request, path, **kwargs):
    """Универсальный обработчик медиа, учитывающий тенанта"""
    # Базовый корень — это корень проекта (так как там лежит tenant_media)
    document_root = settings.MEDIA_ROOT
    
    # Если это запрос от тенанта (не public)
    if hasattr(request, 'tenant') and request.tenant.schema_name != 'public':
        tenant_root = os.path.join(settings.MEDIA_ROOT, request.tenant.schema_name)
        # Если файл существует в папке тенанта (например, abc/tenant_media/...)
        if os.path.exists(os.path.join(tenant_root, path)):
            document_root = tenant_root
    
    return serve(request, path, document_root=document_root, **kwargs)

urlpatterns = [
    path('admin/login/', SuperuserLoginView.as_view(), name='admin_login'),
    path('admin/', admin.site.urls), # Standard admin for public schema
    path('tariffs/', public_tariffs, name='public_tariffs'),
    path('register/', TenantRegistrationViewSet.as_view({'post': 'register'}), name='register'),
    path('superuser/', superuser_dashboard, name='superuser_dashboard'),
    path('superuser/tenants/', superuser_tenants, name='superuser_tenants'),
    path('superuser/tenants/<int:tenant_id>/edit/', superuser_tenant_edit, name='superuser_tenant_edit'),
    path('superuser/tenants/<int:tenant_id>/toggle-status/', superuser_tenant_toggle_status, name='superuser_tenant_toggle_status'),
    path('superuser/tenants/<int:tenant_id>/delete/', superuser_tenant_delete, name='superuser_tenant_delete'),
    path('superuser/domains/', superuser_domains, name='superuser_domains'),
    path('superuser/domains/add/', superuser_domain_create, name='superuser_domain_create'),
    path('superuser/domains/<int:domain_id>/edit/', superuser_domain_edit, name='superuser_domain_edit'),
    path('superuser/domains/<int:domain_id>/delete/', superuser_domain_delete, name='superuser_domain_delete'),
    path('superuser/admins/', superuser_admins, name='superuser_admins'),
    path('superuser/admins/add/', superuser_admin_create, name='superuser_admin_create'),
    path('superuser/admins/<int:user_id>/edit/', superuser_admin_edit, name='superuser_admin_edit'),
    path('superuser/admins/<int:user_id>/delete/', superuser_admin_delete, name='superuser_admin_delete'),
    
    # Администраторы тенантов (управление внутри схемы)
    path('superuser/admins/tenant/<int:tenant_id>/<int:user_id>/edit/', superuser_tenant_admin_edit, name='superuser_tenant_admin_edit'),
    path('superuser/admins/tenant/<int:tenant_id>/<int:user_id>/delete/', superuser_tenant_admin_delete, name='superuser_tenant_admin_delete'),
    
    # Тарифные планы
    path('superuser/plans/', superuser_plans, name='superuser_plans'),
    path('superuser/plans/add/', superuser_plan_create, name='superuser_plan_create'),
    path('superuser/plans/<int:plan_id>/edit/', superuser_plan_edit, name='superuser_plan_edit'),
    path('superuser/plans/<int:plan_id>/delete/', superuser_plan_delete, name='superuser_plan_delete'),
    
    # Финансы
    path('superuser/finance/', superuser_finance, name='superuser_finance'),
    path('superuser/finance/tenant/<int:tenant_id>/', superuser_client_payments, name='superuser_client_payments'),
    path('superuser/finance/tenant/<int:tenant_id>/add-payment/', superuser_payment_add, name='superuser_payment_add'),
    path('superuser/finance/payment/<int:payment_id>/edit/', superuser_payment_edit, name='superuser_payment_edit'),
    path('superuser/finance/payment/<int:payment_id>/delete/', superuser_payment_delete, name='superuser_payment_delete'),
    
    # Настройки почты
    path('superuser/settings/mail/', superuser_mail_settings, name='superuser_mail_settings'),
    
    # Настройки AI
    path('superuser/settings/ai/', superuser_ai_settings, name='superuser_ai_settings'),
    
    # Управление базой данных
    path('superuser/settings/db/', include([
        path('', superuser_db_management, name='superuser_db_management'),
        path('cleanup-tenants/', superuser_db_cleanup_tenants, name='superuser_db_cleanup_tenants'),
        path('vacuum/', superuser_db_vacuum, name='superuser_db_vacuum'),
        path('backup/', superuser_db_backup, name='superuser_db_backup'),
        path('restore/<str:filename>/', superuser_db_restore, name='superuser_db_restore'),
    ])),
    
    # Обратная связь
    path('contact-submit/', contact_form_submit, name='contact_form_submit'),
    path('get-captcha/', get_captcha, name='get_captcha'),
    
    # Логи почты
    path('superuser/mail-logs/', superuser_mail_logs, name='superuser_mail_logs'),
    path('superuser/mail-logs/<int:message_id>/delete/', superuser_mail_log_delete, name='superuser_mail_log_delete'),
    path('superuser/mail-logs/<int:message_id>/edit/', superuser_mail_log_edit, name='superuser_mail_log_edit'),
    
    path('api/customers/', include('customers.urls')),
    path('ai/', include('ai_app.urls')),
    
    # Добавляем маршруты дашборда прямо в основной конфиг,
    # чтобы они были доступны даже если middleware не сработал
    path('login/', dashboard_views.TenantLoginView.as_view(), name='login'),
    path('logout/', dashboard_views.TenantLogoutView.as_view(), name='logout'),
    path('dashboard/', include('dashboard.urls')), 
    
    path('', landing_page, name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += [
        path('media/<path:path>', universal_media_serve),
    ]
