from django.contrib import admin
from dashboard.models import AdminPasswordLog


@admin.register(AdminPasswordLog)
class AdminPasswordLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'admin_user', 'employee_username', 'action', 'password_length', 'ip_address')
    list_filter = ('action', 'timestamp', 'admin_user')
    search_fields = ('employee_username', 'admin_user__username', 'ip_address')
    readonly_fields = ('timestamp', 'ip_address', 'user_agent')
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Информация', {
            'fields': ('admin_user', 'employee_username', 'action', 'timestamp')
        }),
        ('Детали', {
            'fields': ('password_length', 'ip_address', 'user_agent', 'notes')
        }),
    )
