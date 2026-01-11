from django.contrib import admin
from django_tenants.admin import TenantAdminMixin
from .models import Client, Domain, MailSettings, ContactMessage, UserProfile, SubscriptionPlan

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_month', 'max_users', 'storage_gb', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(MailSettings)
class MailSettingsAdmin(admin.ModelAdmin):
    list_display = ('email_host', 'email_host_user', 'default_from_email')

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at', 'is_read', 'is_sent')
    list_filter = ('is_read', 'is_sent', 'created_at')
    search_fields = ('name', 'email', 'message', 'subject', 'ip_address')
    readonly_fields = ('created_at', 'ip_address', 'user_agent', 'error_log')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'tenant', 'role', 'can_delete_media')
    list_filter = ('role', 'can_delete_media')
    search_fields = ('user__username', 'user__email')

class DomainInline(admin.TabularInline):
    model = Domain
    extra = 1

@admin.register(Client)
class ClientAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'schema_name', 'subscription_plan', 'is_active', 'created_on')
    list_filter = ('is_active', 'created_on', 'subscription_end_date')
    search_fields = ('name', 'schema_name', 'phone', 'telegram', 'email', 'contact_person')
    readonly_fields = ('created_on',)
    fieldsets = (
        (None, {
            'fields': ('name', 'schema_name', 'is_active')
        }),
        ('Контакты организации', {
            'fields': ('phone', 'telegram', 'email')
        }),
        ('Обратная связь', {
            'fields': ('contact_person',)
        }),
        ('Подписка', {
            'fields': ('subscription_plan', 'subscription_end_date', 'created_on', 'can_admin_delete_media')
        }),
    )
    inlines = [DomainInline]
    actions = ['activate_tenants', 'deactivate_tenants']

    def activate_tenants(self, request, queryset):
        queryset.update(is_active=True)
    activate_tenants.short_description = "Активировать выбранных тенантов"

    def deactivate_tenants(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_tenants.short_description = "Заблокировать выбранных тенантов"

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('domain', 'tenant', 'is_primary')
    search_fields = ('domain',)
