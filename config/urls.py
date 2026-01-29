from django.contrib import admin

from django.urls import path, include

from django.conf import settings

from django.conf.urls.static import static

from django.views.static import serve

from django.contrib.auth import views as auth_views

import os

from customers.views import (

    landing_page, superuser_dashboard, superuser_tenants, 

    superuser_tenant_edit, superuser_tenant_toggle_status,

    superuser_tenant_delete,

    superuser_domains, superuser_admins, superuser_admin_edit,

    superuser_admin_create, superuser_admin_delete,

    superuser_plans, superuser_plan_create, superuser_plan_edit,

    superuser_plan_delete,

    superuser_finance, superuser_client_payments, superuser_payment_add,

    superuser_payment_edit, superuser_payment_delete,

    superuser_mail_settings, contact_form_submit,

    superuser_mail_logs, get_captcha, superuser_mail_log_delete,

    superuser_mail_log_edit, superuser_ai_settings,

    superuser_db_management, superuser_db_cleanup_tenants, superuser_db_vacuum,

    superuser_db_backup, superuser_db_restore,

    superuser_tenant_admin_edit, superuser_tenant_admin_delete,

    public_tariffs, TenantRegistrationViewSet, SuperuserLoginView,
    
    superuser_templates, superuser_proposals, superuser_template_create,
    superuser_template_edit, superuser_template_delete, superuser_template_diagram,
    superuser_template_save_connection, superuser_template_save_stage,
    superuser_template_add_stage, superuser_template_delete_stage, superuser_template_update_duration,
    
    superuser_materials, superuser_material_create, superuser_material_edit,
    superuser_material_delete, superuser_units, superuser_unit_create,
    superuser_unit_edit, superuser_unit_delete, superuser_positions,
    superuser_position_create, superuser_position_edit, superuser_position_delete

)

from dashboard import views as dashboard_views



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
    
    path('logout/', auth_views.LogoutView.as_view(next_page='/admin/login/'), name='logout'),

    path('admin/', admin.site.urls), # Standard admin for public schema

    path('tariffs/', public_tariffs, name='public_tariffs'),

    path('register/', TenantRegistrationViewSet.as_view({'post': 'register'}), name='register'),

    path('superuser/', superuser_dashboard, name='superuser_dashboard'),

    path('superuser/tenants/', superuser_tenants, name='superuser_tenants'),

    path('superuser/tenants/<int:tenant_id>/edit/', superuser_tenant_edit, name='superuser_tenant_edit'),

    path('superuser/tenants/<int:tenant_id>/toggle-status/', superuser_tenant_toggle_status, name='superuser_tenant_toggle_status'),

    path('superuser/tenants/<int:tenant_id>/delete/', superuser_tenant_delete, name='superuser_tenant_delete'),

    path('superuser/domains/', superuser_domains, name='superuser_domains'),

    path('superuser/admins/', superuser_admins, name='superuser_admins'),

    path('superuser/admins/add/', superuser_admin_create, name='superuser_admin_create'),

    path('superuser/admins/<int:user_id>/edit/', superuser_admin_edit, name='superuser_admin_edit'),

    path('superuser/admins/<int:user_id>/delete/', superuser_admin_delete, name='superuser_admin_delete'),

    

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

    

    # Обратная связь

    path('contact-submit/', contact_form_submit, name='contact_form_submit'),

    path('get-captcha/', get_captcha, name='get_captcha'),

    

    # Логи почты

    path('superuser/mail-logs/', superuser_mail_logs, name='superuser_mail_logs'),

    path('superuser/mail-logs/<int:message_id>/delete/', superuser_mail_log_delete, name='superuser_mail_log_delete'),

    path('superuser/mail-logs/<int:message_id>/edit/', superuser_mail_log_edit, name='superuser_mail_log_edit'),

    

    # Управление БД

    path('superuser/db-management/', superuser_db_management, name='superuser_db_management'),

    path('superuser/db-management/cleanup/', superuser_db_cleanup_tenants, name='superuser_db_cleanup_tenants'),

    path('superuser/db-management/optimize/', superuser_db_vacuum, name='superuser_db_vacuum'),

    path('superuser/db-management/backup/', superuser_db_backup, name='superuser_db_backup'),

    path('superuser/db-management/restore/<str:filename>/', superuser_db_restore, name='superuser_db_restore'),

    

    # Администраторы тенантов

    path('superuser/tenants/<int:tenant_id>/admins/<int:user_id>/edit/', superuser_tenant_admin_edit, name='superuser_tenant_admin_edit'),

    path('superuser/tenants/<int:tenant_id>/admins/<int:user_id>/delete/', superuser_tenant_admin_delete, name='superuser_tenant_admin_delete'),
    
    # Шаблоны и предложения для root-администратора
    path('superuser/templates/', superuser_templates, name='superuser_templates'),
    path('superuser/templates/create/', superuser_template_create, name='superuser_template_create'),
    path('superuser/templates/<int:template_id>/edit/', superuser_template_edit, name='superuser_template_edit'),
    path('superuser/templates/<int:template_id>/delete/', superuser_template_delete, name='superuser_template_delete'),
    path('superuser/templates/<int:template_id>/diagram/', superuser_template_diagram, name='superuser_template_diagram'),
    path('superuser/templates/<int:template_id>/save-connection/', superuser_template_save_connection, name='superuser_template_save_connection'),
    path('superuser/templates/<int:template_id>/save-stage/', superuser_template_save_stage, name='superuser_template_save_stage'),
    path('superuser/templates/<int:template_id>/add-stage/', superuser_template_add_stage, name='superuser_template_add_stage'),
    path('superuser/templates/<int:template_id>/delete-stage/<int:stage_id>/', superuser_template_delete_stage, name='superuser_template_delete_stage'),
    path('superuser/templates/<int:template_id>/update-duration/<int:stage_id>/', superuser_template_update_duration, name='superuser_template_update_duration'),
    path('superuser/proposals/', superuser_proposals, name='superuser_proposals'),
    
    # Справочники: Материалы
    path('superuser/materials/', superuser_materials, name='superuser_materials'),
    path('superuser/materials/create/', superuser_material_create, name='superuser_material_create'),
    path('superuser/materials/<int:material_id>/edit/', superuser_material_edit, name='superuser_material_edit'),
    path('superuser/materials/<int:material_id>/delete/', superuser_material_delete, name='superuser_material_delete'),
    
    # Справочники: Единицы измерения
    path('superuser/units/', superuser_units, name='superuser_units'),
    path('superuser/units/create/', superuser_unit_create, name='superuser_unit_create'),
    path('superuser/units/<int:unit_id>/edit/', superuser_unit_edit, name='superuser_unit_edit'),
    path('superuser/units/<int:unit_id>/delete/', superuser_unit_delete, name='superuser_unit_delete'),
    
    # Справочники: Должности
    path('superuser/positions/', superuser_positions, name='superuser_positions'),
    path('superuser/positions/create/', superuser_position_create, name='superuser_position_create'),
    path('superuser/positions/<int:position_id>/edit/', superuser_position_edit, name='superuser_position_edit'),
    path('superuser/positions/<int:position_id>/delete/', superuser_position_delete, name='superuser_position_delete'),

    

    path('api/customers/', include('customers.urls')),

    path('ai/', include('ai_app.urls')),
    
    path('api/task-templates/', include('task_templates.urls')),
    
    path('', include('dashboard.urls')),

    

    path('', landing_page, name='home'),

]



if settings.DEBUG:

    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    urlpatterns += [

        path('media/<path:path>', universal_media_serve),

    ]

