from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from .models import (
    ActivityCategory,
    TaskTemplate,
    TaskTemplateStage,
    TemplateProposal,
    TemplateAuditLog,
    TemplateFilterPreference,
)
from .serializers import (
    ActivityCategorySerializer,
    TaskTemplateSerializer,
    TaskTemplateDetailSerializer,
    TaskTemplateStageSerializer,
    TemplateProposalSerializer,
    TemplateProposalDetailSerializer,
    TemplateAuditLogSerializer,
    TemplateFilterPreferenceSerializer,
    CreateTemplateSerializer,
    AddStageSerializer,
    UpdateStageSerializer,
    ReorderStagesSerializer,
    CreateProposalSerializer,
    UpdateProposalSerializer,
    ApproveProposalSerializer,
    RejectProposalSerializer,
    SetFilterPreferenceSerializer,
)
from .services import (
    TemplateService,
    LocalTemplateService,
    ProposalService,
    FilterService,
)


class ActivityCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API для получения категорий деятельности
    
    Endpoints:
    - GET /api/categories/ - Список всех категорий
    - GET /api/categories/{id}/ - Получение деталей категории
    """
    
    queryset = ActivityCategory.objects.filter(is_active=True)
    serializer_class = ActivityCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ['name']
    ordering = ['name']


class TaskTemplateViewSet(viewsets.ModelViewSet):
    """
    API для управления шаблонами задач
    
    Endpoints:
    - GET /api/templates/ - Список шаблонов (с фильтрацией)
    - POST /api/templates/ - Создание нового шаблона
    - GET /api/templates/{id}/ - Получение деталей шаблона
    - PUT /api/templates/{id}/ - Обновление шаблона
    - DELETE /api/templates/{id}/ - Удаление шаблона
    - POST /api/templates/{id}/add-stage/ - Добавление этапа
    - PUT /api/templates/{id}/stages/{stage_id}/ - Обновление этапа
    - DELETE /api/templates/{id}/stages/{stage_id}/ - Удаление этапа
    - POST /api/templates/{id}/reorder-stages/ - Переупорядочение этапов
    - POST /api/templates/{id}/create-local-variant/ - Создание локального варианта
    """
    
    queryset = TaskTemplate.objects.all()
    serializer_class = TaskTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['template_type', 'activity_category', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Выбрать сериализатор в зависимости от действия"""
        if self.action == 'retrieve':
            return TaskTemplateDetailSerializer
        elif self.action == 'create':
            return CreateTemplateSerializer
        elif self.action == 'add_stage':
            return AddStageSerializer
        elif self.action == 'update_stage':
            return UpdateStageSerializer
        elif self.action == 'reorder_stages':
            return ReorderStagesSerializer
        elif self.action == 'create_local_variant':
            return CreateTemplateSerializer
        return TaskTemplateSerializer
    
    def create(self, request, *args, **kwargs):
        """Создать новый шаблон"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            if serializer.validated_data.get('template_type') == 'local':
                template = LocalTemplateService.create_local_template(
                    name=serializer.validated_data['name'],
                    description=serializer.validated_data.get('description', ''),
                    activity_category=serializer.validated_data['activity_category'],
                    created_by=request.user,
                    based_on_global=serializer.validated_data.get('based_on_global'),
                )
            else:
                template = TemplateService.create_template(
                    name=serializer.validated_data['name'],
                    description=serializer.validated_data.get('description', ''),
                    activity_category=serializer.validated_data['activity_category'],
                    created_by=request.user,
                    template_type='global',
                )
            
            output_serializer = TaskTemplateDetailSerializer(template)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        
        except ValidationError as e:
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, *args, **kwargs):
        """Обновить шаблон"""
        template = self.get_object()
        
        try:
            if template.template_type == 'local':
                template = LocalTemplateService.update_local_template(
                    template=template,
                    name=request.data.get('name'),
                    description=request.data.get('description'),
                    activity_category=request.data.get('activity_category'),
                    updated_by=request.user,
                )
            else:
                template = TemplateService.update_template(
                    template=template,
                    name=request.data.get('name'),
                    description=request.data.get('description'),
                    activity_category=request.data.get('activity_category'),
                    updated_by=request.user,
                )
            
            serializer = TaskTemplateDetailSerializer(template)
            return Response(serializer.data)
        
        except ValidationError as e:
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        """Удалить шаблон"""
        template = self.get_object()
        
        try:
            if template.template_type == 'local':
                LocalTemplateService.delete_local_template(template, request.user)
            else:
                TemplateService.delete_template(template, request.user)
            
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        except ValidationError as e:
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_stage(self, request, pk=None):
        """Добавить этап к шаблону"""
        template = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            stage = TemplateService.add_stage(
                template=template,
                name=serializer.validated_data['name'],
                description=serializer.validated_data.get('description', ''),
                estimated_duration_hours=serializer.validated_data['estimated_duration_hours'],
                sequence_number=serializer.validated_data.get('sequence_number'),
            )
            
            output_serializer = TaskTemplateStageSerializer(stage)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        
        except ValidationError as e:
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['put'], url_path=r'stages/(?P<stage_id>\d+)')
    def update_stage(self, request, pk=None, stage_id=None):
        """Обновить этап шаблона"""
        template = self.get_object()
        stage = get_object_or_404(TaskTemplateStage, id=stage_id, template=template)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            stage = TemplateService.update_stage(
                stage=stage,
                name=serializer.validated_data.get('name'),
                description=serializer.validated_data.get('description'),
                estimated_duration_hours=serializer.validated_data.get('estimated_duration_hours'),
            )
            
            output_serializer = TaskTemplateStageSerializer(stage)
            return Response(output_serializer.data)
        
        except ValidationError as e:
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'], url_path=r'stages/(?P<stage_id>\d+)')
    def delete_stage(self, request, pk=None, stage_id=None):
        """Удалить этап из шаблона"""
        template = self.get_object()
        stage = get_object_or_404(TaskTemplateStage, id=stage_id, template=template)
        
        try:
            TemplateService.delete_stage(stage)
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        except ValidationError as e:
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def reorder_stages(self, request, pk=None):
        """Переупорядочить этапы в шаблоне"""
        template = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            TemplateService.reorder_stages(
                template=template,
                stage_order=serializer.validated_data['stage_order'],
            )
            
            template.refresh_from_db()
            output_serializer = TaskTemplateDetailSerializer(template)
            return Response(output_serializer.data)
        
        except ValidationError as e:
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def create_local_variant(self, request, pk=None):
        """Создать локальный вариант глобального шаблона"""
        global_template = self.get_object()
        
        if global_template.template_type != 'global':
            return Response(
                {'error': 'Можно создавать локальные варианты только для глобальных шаблонов'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            local_template = LocalTemplateService.create_local_template(
                name=serializer.validated_data['name'],
                description=serializer.validated_data.get('description', ''),
                activity_category=serializer.validated_data['activity_category'],
                created_by=request.user,
                based_on_global=global_template,
            )
            
            output_serializer = TaskTemplateDetailSerializer(local_template)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        
        except ValidationError as e:
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)


class TemplateProposalViewSet(viewsets.ModelViewSet):
    """
    API для управления предложениями шаблонов
    
    Endpoints:
    - GET /api/proposals/ - Список предложений
    - POST /api/proposals/ - Создание нового предложения
    - GET /api/proposals/{id}/ - Получение деталей предложения
    - PUT /api/proposals/{id}/ - Обновление предложения (только в статусе "ожидание")
    - DELETE /api/proposals/{id}/ - Отзыв предложения (только в статусе "ожидание")
    - POST /api/proposals/{id}/approve/ - Одобрение предложения (только для root-администратора)
    - POST /api/proposals/{id}/reject/ - Отклонение предложения (только для root-администратора)
    """
    
    queryset = TemplateProposal.objects.all()
    serializer_class = TemplateProposalSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'proposed_by']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Выбрать сериализатор в зависимости от действия"""
        if self.action == 'retrieve':
            return TemplateProposalDetailSerializer
        elif self.action == 'create':
            return CreateProposalSerializer
        elif self.action == 'update':
            return UpdateProposalSerializer
        elif self.action == 'approve':
            return ApproveProposalSerializer
        elif self.action == 'reject':
            return RejectProposalSerializer
        return TemplateProposalSerializer
    
    def create(self, request, *args, **kwargs):
        """Создать новое предложение"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            proposal = ProposalService.create_proposal(
                local_template=serializer.validated_data['local_template'],
                proposed_by=request.user,
            )
            
            output_serializer = TemplateProposalDetailSerializer(proposal)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        
        except ValidationError as e:
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, *args, **kwargs):
        """Обновить предложение"""
        proposal = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            proposal = ProposalService.update_proposal(
                proposal=proposal,
                name=serializer.validated_data.get('name'),
                description=serializer.validated_data.get('description'),
                updated_by=request.user,
            )
            
            output_serializer = TemplateProposalDetailSerializer(proposal)
            return Response(output_serializer.data)
        
        except ValidationError as e:
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        """Отозвать предложение"""
        proposal = self.get_object()
        
        try:
            ProposalService.withdraw_proposal(proposal, request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        except ValidationError as e:
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Одобрить предложение"""
        proposal = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            global_template = ProposalService.approve_proposal(
                proposal=proposal,
                approved_by=request.user,
            )
            
            output_serializer = TaskTemplateDetailSerializer(global_template)
            return Response(output_serializer.data)
        
        except ValidationError as e:
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Отклонить предложение"""
        proposal = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            ProposalService.reject_proposal(
                proposal=proposal,
                rejection_reason=serializer.validated_data.get('rejection_reason', ''),
                rejected_by=request.user,
            )
            
            proposal.refresh_from_db()
            output_serializer = TemplateProposalDetailSerializer(proposal)
            return Response(output_serializer.data)
        
        except ValidationError as e:
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)


class TemplateFilterPreferenceViewSet(viewsets.ViewSet):
    """
    API для управления предпочтениями фильтра
    
    Endpoints:
    - GET /api/filter-preferences/me/ - Получить предпочтения текущего пользователя
    - PUT /api/filter-preferences/me/ - Обновить предпочтения текущего пользователя
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Получить предпочтения текущего пользователя"""
        preference = FilterService.get_user_filter_preference(request.user)
        
        if preference:
            serializer = TemplateFilterPreferenceSerializer(preference)
            return Response(serializer.data)
        else:
            return Response({
                'show_all_categories': False,
                'last_category_filter': None,
            })
    
    @action(detail=False, methods=['put'])
    def set_preference(self, request):
        """Установить предпочтения текущего пользователя"""
        serializer = SetFilterPreferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        preference = FilterService.set_filter_preference(
            user=request.user,
            show_all_categories=serializer.validated_data.get('show_all_categories', False),
            last_category_filter=serializer.validated_data.get('last_category_filter'),
        )
        
        output_serializer = TemplateFilterPreferenceSerializer(preference)
        return Response(output_serializer.data)
