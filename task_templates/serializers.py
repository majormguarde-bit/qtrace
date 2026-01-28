from rest_framework import serializers
from .models import (
    ActivityCategory,
    TaskTemplate,
    TaskTemplateStage,
    TemplateProposal,
    TemplateAuditLog,
    TemplateFilterPreference,
    DurationUnit,
)


class ActivityCategorySerializer(serializers.ModelSerializer):
    """Сериализатор для категорий деятельности"""
    
    class Meta:
        model = ActivityCategory
        fields = ('id', 'name', 'description', 'slug', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')


class TaskTemplateStageSerializer(serializers.ModelSerializer):
    """Сериализатор для этапов шаблона"""
    
    duration_unit_name = serializers.CharField(source='duration_unit.name', read_only=True)
    
    class Meta:
        model = TaskTemplateStage
        fields = (
            'id',
            'template',
            'name',
            'description',
            'estimated_duration',
            'duration_unit',
            'duration_unit_name',
            'sequence_number',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')
    
    def validate_estimated_duration(self, value):
        """Валидация длительности этапа"""
        if value < 0.01:
            raise serializers.ValidationError('Минимальная длительность 0.01')
        return value
    
    def validate_name(self, value):
        """Валидация названия этапа"""
        if not value or not value.strip():
            raise serializers.ValidationError('Название этапа обязательно')
        return value.strip()


class TaskTemplateSerializer(serializers.ModelSerializer):
    """Сериализатор для шаблонов задач"""
    
    stages = TaskTemplateStageSerializer(many=True, read_only=True)
    activity_category_name = serializers.CharField(
        source='activity_category.name',
        read_only=True
    )
    created_by_username = serializers.CharField(
        source='created_by.username',
        read_only=True
    )
    updated_by_username = serializers.CharField(
        source='updated_by.username',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = TaskTemplate
        fields = (
            'id',
            'name',
            'description',
            'template_type',
            'activity_category',
            'activity_category_name',
            'based_on_global',
            'version',
            'is_active',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_by',
            'updated_by_username',
            'updated_at',
            'stages',
        )
        read_only_fields = (
            'version',
            'created_by',
            'created_at',
            'updated_by',
            'updated_at',
            'stages',
        )
    
    def validate_name(self, value):
        """Валидация названия шаблона"""
        if not value or not value.strip():
            raise serializers.ValidationError('Название шаблона обязательно')
        return value.strip()
    
    def validate_activity_category(self, value):
        """Валидация категории"""
        if not value:
            raise serializers.ValidationError('Категория деятельности обязательна')
        return value


class TaskTemplateDetailSerializer(TaskTemplateSerializer):
    """Расширенный сериализатор для деталей шаблона"""
    
    based_on_global_name = serializers.CharField(
        source='based_on_global.name',
        read_only=True,
        allow_null=True
    )
    local_variants_count = serializers.SerializerMethodField()
    
    class Meta(TaskTemplateSerializer.Meta):
        fields = TaskTemplateSerializer.Meta.fields + (
            'based_on_global_name',
            'local_variants_count',
        )
    
    def get_local_variants_count(self, obj):
        """Получить количество локальных вариантов"""
        if obj.template_type == 'global':
            return obj.local_variants.count()
        return None


class TemplateProposalSerializer(serializers.ModelSerializer):
    """Сериализатор для предложений шаблонов"""
    
    local_template_name = serializers.CharField(
        source='local_template.name',
        read_only=True
    )
    proposed_by_username = serializers.CharField(
        source='proposed_by.username',
        read_only=True
    )
    reviewed_by_username = serializers.CharField(
        source='reviewed_by.username',
        read_only=True,
        allow_null=True
    )
    approved_global_template_name = serializers.CharField(
        source='approved_global_template.name',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = TemplateProposal
        fields = (
            'id',
            'local_template',
            'local_template_name',
            'proposed_by',
            'proposed_by_username',
            'status',
            'approved_global_template',
            'approved_global_template_name',
            'rejection_reason',
            'created_at',
            'reviewed_by',
            'reviewed_by_username',
            'reviewed_at',
        )
        read_only_fields = (
            'proposed_by',
            'status',
            'approved_global_template',
            'rejection_reason',
            'created_at',
            'reviewed_by',
            'reviewed_at',
        )


class TemplateProposalDetailSerializer(TemplateProposalSerializer):
    """Расширенный сериализатор для деталей предложения"""
    
    local_template = TaskTemplateDetailSerializer(read_only=True)
    approved_global_template = TaskTemplateDetailSerializer(read_only=True, allow_null=True)
    
    class Meta(TemplateProposalSerializer.Meta):
        pass


class TemplateAuditLogSerializer(serializers.ModelSerializer):
    """Сериализатор для журнала аудита"""
    
    template_name = serializers.CharField(
        source='template.name',
        read_only=True,
        allow_null=True
    )
    proposal_template_name = serializers.CharField(
        source='proposal.local_template.name',
        read_only=True,
        allow_null=True
    )
    performed_by_username = serializers.CharField(
        source='performed_by.username',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = TemplateAuditLog
        fields = (
            'id',
            'action',
            'template',
            'template_name',
            'proposal',
            'proposal_template_name',
            'performed_by',
            'performed_by_username',
            'changes',
            'created_at',
        )
        read_only_fields = (
            'action',
            'template',
            'proposal',
            'performed_by',
            'changes',
            'created_at',
        )


class TemplateFilterPreferenceSerializer(serializers.ModelSerializer):
    """Сериализатор для предпочтений фильтра"""
    
    user_username = serializers.CharField(
        source='user.username',
        read_only=True
    )
    last_category_filter_name = serializers.CharField(
        source='last_category_filter.name',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = TemplateFilterPreference
        fields = (
            'id',
            'user',
            'user_username',
            'show_all_categories',
            'last_category_filter',
            'last_category_filter_name',
            'updated_at',
        )
        read_only_fields = ('user', 'updated_at')


class CreateTemplateSerializer(serializers.Serializer):
    """Сериализатор для создания шаблона"""
    
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    activity_category = serializers.PrimaryKeyRelatedField(
        queryset=ActivityCategory.objects.all()
    )
    template_type = serializers.ChoiceField(
        choices=['global', 'local'],
        default='global'
    )
    based_on_global = serializers.PrimaryKeyRelatedField(
        queryset=TaskTemplate.objects.filter(template_type='global'),
        required=False,
        allow_null=True
    )
    
    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Название шаблона обязательно')
        return value.strip()
    
    def validate_activity_category(self, value):
        if not value:
            raise serializers.ValidationError('Категория деятельности обязательна')
        return value


class AddStageSerializer(serializers.Serializer):
    """Сериализатор для добавления этапа"""
    
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    estimated_duration = serializers.DecimalField(max_digits=10, decimal_places=2)
    duration_unit = serializers.PrimaryKeyRelatedField(queryset=DurationUnit.objects.all())
    sequence_number = serializers.IntegerField(required=False, allow_null=True)
    
    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Название этапа обязательно')
        return value.strip()
    
    def validate_estimated_duration(self, value):
        if value < 0.01:
            raise serializers.ValidationError('Минимальная длительность 0.01')
        return value


class UpdateStageSerializer(serializers.Serializer):
    """Сериализатор для обновления этапа"""
    
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    estimated_duration = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False
    )
    duration_unit = serializers.PrimaryKeyRelatedField(
        queryset=DurationUnit.objects.all(),
        required=False
    )
    
    def validate_name(self, value):
        if value and not value.strip():
            raise serializers.ValidationError('Название этапа обязательно')
        return value.strip() if value else None
    
    def validate_estimated_duration(self, value):
        if value and value < 0.01:
            raise serializers.ValidationError('Минимальная длительность 0.01')
        return value


class ReorderStagesSerializer(serializers.Serializer):
    """Сериализатор для переупорядочения этапов"""
    
    stage_order = serializers.ListField(
        child=serializers.IntegerField(),
        help_text='Список ID этапов в новом порядке'
    )


class CreateProposalSerializer(serializers.Serializer):
    """Сериализатор для создания предложения"""
    
    local_template = serializers.PrimaryKeyRelatedField(
        queryset=TaskTemplate.objects.filter(template_type='local')
    )


class UpdateProposalSerializer(serializers.Serializer):
    """Сериализатор для обновления предложения"""
    
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    
    def validate_name(self, value):
        if value and not value.strip():
            raise serializers.ValidationError('Название шаблона обязательно')
        return value.strip() if value else None


class ApproveProposalSerializer(serializers.Serializer):
    """Сериализатор для одобрения предложения"""
    
    pass  # Нет дополнительных полей


class RejectProposalSerializer(serializers.Serializer):
    """Сериализатор для отклонения предложения"""
    
    rejection_reason = serializers.CharField(required=False, allow_blank=True)


class SetFilterPreferenceSerializer(serializers.Serializer):
    """Сериализатор для установки предпочтений фильтра"""
    
    show_all_categories = serializers.BooleanField(default=False)
    last_category_filter = serializers.PrimaryKeyRelatedField(
        queryset=ActivityCategory.objects.all(),
        required=False,
        allow_null=True
    )
