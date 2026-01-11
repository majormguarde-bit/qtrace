from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import TenantUser, Department
from customers.models import UserProfile


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """Админ-панель для подразделений"""
    list_display = ('name', 'parent', 'created_at')
    list_filter = ('parent', 'created_at')
    search_fields = ('name', 'description')


class TenantUserAdmin(admin.ModelAdmin):
    """Админ-панель для пользователей тенанта"""
    list_display = ('username', 'email', 'role', 'position', 'department', 'phone', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'department', 'created_at')
    search_fields = ('username', 'email', 'phone', 'position')
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password_hash')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone', 'position', 'department')}),
        (_('Permissions'), {'fields': ('role', 'is_active')}),
        (_('Important dates'), {'fields': ('created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at', 'password_hash')
    
    def get_queryset(self, request):
        """Фильтровать пользователей по текущему тенанту"""
        qs = super().get_queryset(request)
        # Если есть контекст тенанта, фильтруем по нему
        if hasattr(request, 'tenant') and request.tenant:
            # Все пользователи в текущем тенанте уже отфильтрованы
            # благодаря TenantSyncRouter
            return qs
        return qs
    
    def delete_view(self, request, object_id, extra_context=None):
        """Переопределить delete_view для избежания ошибок"""
        if request.method == 'POST':
            try:
                obj = self.get_object(request, object_id)
                obj_display = str(obj)
                obj.delete()
                self.message_user(request, f'Пользователь "{obj_display}" успешно удален.', messages.SUCCESS)
                return HttpResponseRedirect(reverse(f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist'))
            except Exception as e:
                self.message_user(request, f'Ошибка при удалении: {str(e)}', messages.ERROR)
                return HttpResponseRedirect(reverse(f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist'))
        
        return super().delete_view(request, object_id, extra_context)


class UserProfileAdmin(admin.ModelAdmin):
    """Админ-панель для профилей пользователей (public schema)"""
    list_display = ('user', 'role')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email')


# Переопределить UserAdmin для public schema
class CustomUserAdmin(BaseUserAdmin):
    """Админ-панель для пользователей public schema"""
    list_display = ('username', 'email', 'get_full_name', 'get_role', 'is_staff')
    list_filter = ('is_staff', 'is_active', 'date_joined')
    
    def get_role(self, obj):
        """Получить роль пользователя"""
        try:
            return obj.profile.get_role_display()
        except:
            return 'N/A'
    get_role.short_description = 'Role'
    
    def has_add_permission(self, request):
        """Запретить добавление пользователей в tenant schema"""
        if hasattr(request, 'tenant') and request.tenant:
            return False
        return super().has_add_permission(request)
    
    def has_change_permission(self, request, obj=None):
        """Запретить изменение пользователей в tenant schema"""
        if hasattr(request, 'tenant') and request.tenant:
            return False
        return super().has_change_permission(request, obj)
    
    def has_delete_permission(self, request, obj=None):
        """Запретить удаление пользователей в tenant schema"""
        if hasattr(request, 'tenant') and request.tenant:
            return False
        return super().has_delete_permission(request, obj)
    
    def has_view_permission(self, request, obj=None):
        """Запретить просмотр пользователей в tenant schema"""
        if hasattr(request, 'tenant') and request.tenant:
            return False
        return super().has_view_permission(request, obj)


# Зарегистрировать в стандартном админ-сайте
if admin.site.is_registered(User):
    admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(TenantUser, TenantUserAdmin)
