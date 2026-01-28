from django.contrib import admin
from .models import (
    ActivityCategory,
    TaskTemplate,
    TaskTemplateStage,
    TemplateProposal,
    TemplateAuditLog,
    TemplateFilterPreference,
)


@admin.register(ActivityCategory)
class ActivityCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


class TaskTemplateStageInline(admin.TabularInline):
    model = TaskTemplateStage
    extra = 1
    fields = ('name', 'description', 'estimated_duration', 'duration_unit', 'sequence_number')


@admin.register(TaskTemplate)
class TaskTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'template_type', 'activity_category', 'version', 'is_active', 'created_at')
    list_filter = ('template_type', 'activity_category', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    inlines = [TaskTemplateStageInline]
    readonly_fields = ('created_at', 'updated_at', 'created_by_id', 'updated_by_id')


@admin.register(TaskTemplateStage)
class TaskTemplateStageAdmin(admin.ModelAdmin):
    list_display = ('name', 'template', 'sequence_number', 'duration_from', 'duration_to', 'duration_unit', 'position', 'created_at')
    list_filter = ('template', 'created_at')
    search_fields = ('name', 'template__name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(TemplateProposal)
class TemplateProposalAdmin(admin.ModelAdmin):
    list_display = ('local_template', 'proposed_by_id', 'status', 'created_at', 'reviewed_at')
    list_filter = ('status', 'created_at', 'reviewed_at')
    search_fields = ('local_template__name',)
    readonly_fields = ('created_at', 'reviewed_at')


@admin.register(TemplateAuditLog)
class TemplateAuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'template', 'proposal', 'performed_by_id', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('template__name', 'proposal__local_template__name')
    readonly_fields = ('created_at', 'action', 'template', 'proposal', 'performed_by_id', 'changes')


@admin.register(TemplateFilterPreference)
class TemplateFilterPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'show_all_categories', 'last_category_filter', 'updated_at')
    list_filter = ('show_all_categories', 'updated_at')
    readonly_fields = ('updated_at',)
