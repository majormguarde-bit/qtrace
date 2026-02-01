from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import F, Max
from .models import (
    TaskTemplate,
    TaskTemplateStage,
    TemplateProposal,
    TemplateAuditLog,
    TemplateFilterPreference,
    ActivityCategory,
)


class TemplateService:
    """Сервис для управления глобальными шаблонами"""
    
    @staticmethod
    def create_template(name, description, activity_category, created_by, template_type='global'):
        """
        Создать новый шаблон задачи
        
        Args:
            name: Название шаблона
            description: Описание шаблона
            activity_category: Объект ActivityCategory
            created_by: Пользователь, создавший шаблон
            template_type: Тип шаблона ('global' или 'local')
            
        Returns:
            TaskTemplate: Созданный шаблон
            
        Raises:
            ValidationError: Если обязательные поля отсутствуют
        """
        # Валидация обязательных полей
        if not name or not name.strip():
            raise ValidationError({'name': 'Название шаблона обязательно'})
        
        if not activity_category:
            raise ValidationError({'activity_category': 'Категория деятельности обязательна'})
        
        with transaction.atomic():
            template = TaskTemplate.objects.create(
                name=name.strip(),
                description=description or '',
                activity_category=activity_category,
                created_by_id=created_by if isinstance(created_by, int) else (created_by.id if created_by else None),
                template_type=template_type,
                version=1,
                is_active=True,
            )
            
            # Логирование в аудит
            TemplateAuditLog.objects.create(
                action='create',
                template=template,
                performed_by_id=created_by if isinstance(created_by, int) else (created_by.id if created_by else None),
                changes={
                    'name': name,
                    'description': description,
                    'activity_category': activity_category.name,
                    'template_type': template_type,
                }
            )
        
        return template
    
    @staticmethod
    def update_template(template, name=None, description=None, activity_category=None, updated_by=None):
        """
        Обновить существующий шаблон
        
        Args:
            template: Объект TaskTemplate
            name: Новое название (опционально)
            description: Новое описание (опционально)
            activity_category: Новая категория (опционально)
            updated_by: Пользователь, обновивший шаблон
            
        Returns:
            TaskTemplate: Обновленный шаблон
            
        Raises:
            ValidationError: Если данные невалидны
        """
        changes = {}
        
        if name is not None:
            if not name or not name.strip():
                raise ValidationError({'name': 'Название шаблона обязательно'})
            if template.name != name:
                changes['name'] = {'old': template.name, 'new': name}
                template.name = name.strip()
        
        if description is not None:
            if template.description != description:
                changes['description'] = {'old': template.description, 'new': description}
                template.description = description or ''
        
        if activity_category is not None:
            if template.activity_category != activity_category:
                changes['activity_category'] = {
                    'old': template.activity_category.name,
                    'new': activity_category.name
                }
                template.activity_category = activity_category
        
        if changes:
            template.updated_by_id = updated_by if isinstance(updated_by, int) else (updated_by.id if updated_by else None)
            template.version += 1
            
            with transaction.atomic():
                template.save()
                
                # Логирование в аудит
                TemplateAuditLog.objects.create(
                    action='update',
                    template=template,
                    performed_by_id=updated_by if isinstance(updated_by, int) else (updated_by.id if updated_by else None),
                    changes=changes
                )
        
        return template
    
    @staticmethod
    def delete_template(template, deleted_by=None):
        """
        Удалить шаблон
        
        Args:
            template: Объект TaskTemplate
            deleted_by: Пользователь, удаливший шаблон
            
        Raises:
            ValidationError: Если шаблон имеет ожидающие предложения
        """
        # Проверка на ожидающие предложения
        pending_proposals = TemplateProposal.objects.filter(
            local_template=template,
            status='pending'
        ).exists()
        
        if pending_proposals:
            raise ValidationError(
                'Невозможно удалить шаблон с ожидающими предложениями'
            )
        
        with transaction.atomic():
            # Логирование в аудит перед удалением
            TemplateAuditLog.objects.create(
                action='delete',
                template=template,
                performed_by_id=deleted_by if isinstance(deleted_by, int) else (deleted_by.id if deleted_by else None),
                changes={
                    'name': template.name,
                    'template_type': template.template_type,
                }
            )
            
            template.delete()
    
    @staticmethod
    def get_templates_by_category(category, template_type='global', is_active=True):
        """
        Получить шаблоны по категории
        
        Args:
            category: Объект ActivityCategory
            template_type: Тип шаблона ('global' или 'local')
            is_active: Только активные шаблоны
            
        Returns:
            QuerySet: Отфильтрованные шаблоны
        """
        queryset = TaskTemplate.objects.filter(
            activity_category=category,
            template_type=template_type,
        )
        
        if is_active:
            queryset = queryset.filter(is_active=True)
        
        return queryset.prefetch_related('stages')
    
    @staticmethod
    def add_stage(template, name, description, estimated_duration_hours, sequence_number=None):
        """
        Добавить этап к шаблону
        
        Args:
            template: Объект TaskTemplate
            name: Название этапа
            description: Описание этапа
            estimated_duration_hours: Предполагаемая длительность в часах
            sequence_number: Номер последовательности (если None, добавляется в конец)
            
        Returns:
            TaskTemplateStage: Созданный этап
            
        Raises:
            ValidationError: Если данные невалидны
        """
        # Валидация
        if not name or not name.strip():
            raise ValidationError({'name': 'Название этапа обязательно'})
        
        try:
            duration = float(estimated_duration_hours)
            if duration < 0.5:
                raise ValidationError(
                    {'estimated_duration_hours': 'Минимальная длительность 0.5 часа'}
                )
        except (ValueError, TypeError):
            raise ValidationError(
                {'estimated_duration_hours': 'Длительность должна быть числом'}
            )
        
        with transaction.atomic():
            # Если sequence_number не указан, добавляем в конец
            if sequence_number is None:
                max_sequence = TaskTemplateStage.objects.filter(
                    template=template
                ).aggregate(Max('sequence_number'))['sequence_number__max'] or 0
                sequence_number = max_sequence + 1
            else:
                # Если указан, сдвигаем остальные этапы
                TaskTemplateStage.objects.filter(
                    template=template,
                    sequence_number__gte=sequence_number
                ).update(sequence_number=F('sequence_number') + 1)
            
            stage = TaskTemplateStage.objects.create(
                template=template,
                name=name.strip(),
                description=description or '',
                estimated_duration_hours=duration,
                sequence_number=sequence_number,
            )
            
            # Логирование в аудит
            TemplateAuditLog.objects.create(
                action='update',
                template=template,
                performed_by_id=None,
                changes={
                    'action': 'add_stage',
                    'stage_name': name,
                    'sequence_number': sequence_number,
                }
            )
        
        return stage
    
    @staticmethod
    def update_stage(stage, name=None, description=None, estimated_duration_hours=None):
        """
        Обновить этап шаблона
        
        Args:
            stage: Объект TaskTemplateStage
            name: Новое название (опционально)
            description: Новое описание (опционально)
            estimated_duration_hours: Новая длительность (опционально)
            
        Returns:
            TaskTemplateStage: Обновленный этап
            
        Raises:
            ValidationError: Если данные невалидны
        """
        changes = {}
        
        if name is not None:
            if not name or not name.strip():
                raise ValidationError({'name': 'Название этапа обязательно'})
            if stage.name != name:
                changes['name'] = {'old': stage.name, 'new': name}
                stage.name = name.strip()
        
        if description is not None:
            if stage.description != description:
                changes['description'] = {'old': stage.description, 'new': description}
                stage.description = description or ''
        
        if estimated_duration_hours is not None:
            try:
                duration = float(estimated_duration_hours)
                if duration < 0.5:
                    raise ValidationError(
                        {'estimated_duration_hours': 'Минимальная длительность 0.5 часа'}
                    )
                if stage.estimated_duration_hours != duration:
                    changes['estimated_duration_hours'] = {
                        'old': float(stage.estimated_duration_hours),
                        'new': duration
                    }
                    stage.estimated_duration_hours = duration
            except (ValueError, TypeError):
                raise ValidationError(
                    {'estimated_duration_hours': 'Длительность должна быть числом'}
                )
        
        if changes:
            with transaction.atomic():
                stage.save()
                
                # Логирование в аудит
                TemplateAuditLog.objects.create(
                    action='update',
                    template=stage.template,
                    performed_by_id=None,
                    changes={
                        'action': 'update_stage',
                        'stage_id': stage.id,
                        'changes': changes,
                    }
                )
        
        return stage
    
    @staticmethod
    def delete_stage(stage):
        """
        Удалить этап из шаблона
        
        Args:
            stage: Объект TaskTemplateStage
        """
        template = stage.template
        sequence_number = stage.sequence_number
        
        with transaction.atomic():
            # Логирование в аудит перед удалением
            TemplateAuditLog.objects.create(
                action='update',
                template=template,
                performed_by_id=None,
                changes={
                    'action': 'delete_stage',
                    'stage_name': stage.name,
                    'sequence_number': sequence_number,
                }
            )
            
            stage.delete()
            
            # Сдвигаем номера последовательности для оставшихся этапов
            TaskTemplateStage.objects.filter(
                template=template,
                sequence_number__gt=sequence_number
            ).update(sequence_number=F('sequence_number') - 1)
    
    @staticmethod
    def reorder_stages(template, stage_order):
        """
        Переупорядочить этапы в шаблоне
        
        Args:
            template: Объект TaskTemplate
            stage_order: Список ID этапов в новом порядке
            
        Raises:
            ValidationError: Если порядок невалиден
        """
        # Валидация
        existing_stages = set(
            TaskTemplateStage.objects.filter(template=template).values_list('id', flat=True)
        )
        provided_stages = set(stage_order)
        
        if existing_stages != provided_stages:
            raise ValidationError('Порядок этапов содержит неверные ID')
        
        with transaction.atomic():
            for sequence_number, stage_id in enumerate(stage_order, start=1):
                TaskTemplateStage.objects.filter(id=stage_id).update(
                    sequence_number=sequence_number
                )
            
            # Логирование в аудит
            TemplateAuditLog.objects.create(
                action='update',
                template=template,
                performed_by_id=None,
                changes={
                    'action': 'reorder_stages',
                    'new_order': stage_order,
                }
            )

    @staticmethod
    def convert_to_n8n(template):
        """
        Конвертировать шаблон задачи в формат n8n workflow JSON
        
        Args:
            template: Объект TaskTemplate
            
        Returns:
            dict: Структура workflow n8n
        """
        nodes = []
        connections = {}
        
        # 1. Начальный узел (Manual Trigger)
        trigger_node_name = "Start Process"
        nodes.append({
            "parameters": {},
            "name": trigger_node_name,
            "type": "n8n-nodes-base.manualTrigger",
            "typeVersion": 1,
            "position": [250, 300],
            "id": "trigger-node-id"
        })
        
        # 2. Узлы для этапов
        previous_node_name = trigger_node_name
        x_pos = 500
        y_pos = 300
        
        stages = template.stages.all().order_by('sequence_number')
        
        for i, stage in enumerate(stages):
            node_name = f"Stage: {stage.name}"
            
            # Construct duration string
            duration_str = f"{stage.duration_from}"
            if stage.duration_to and stage.duration_to != stage.duration_from:
                duration_str += f"-{stage.duration_to}"
            
            if stage.duration_unit:
                duration_str += f" {stage.duration_unit.name}"
            
            # Формируем данные этапа в Set ноде
            nodes.append({
                "parameters": {
                    "values": {
                        "string": [
                            {"name": "stage_name", "value": stage.name},
                            {"name": "duration", "value": duration_str}
                        ]
                    },
                    "options": {}
                },
                "name": node_name,
                "type": "n8n-nodes-base.set",
                "typeVersion": 1,
                "position": [x_pos, y_pos],
                "id": f"stage-node-{stage.id}"
            })
            
            # Создаем связь с предыдущим узлом
            if previous_node_name not in connections:
                connections[previous_node_name] = {"main": []}
            
            # Ensure the list of outputs exists (usually index 0 for main output)
            if not connections[previous_node_name]["main"]:
                connections[previous_node_name]["main"].append([])
                
            connections[previous_node_name]["main"][0].append({
                "node": node_name,
                "type": "main",
                "index": 0
            })
            
            previous_node_name = node_name
            x_pos += 250
            
        # Формируем итоговую структуру
        workflow = {
            "name": f"Template: {template.name}",
            "nodes": nodes,
            "connections": connections,
            "active": False,
            "settings": {},
            "meta": {
                "templateId": template.id,
                "generatedBy": "Q-TRACE",
                "generatedAt": str(timezone.now())
            }
        }
        
        return workflow


class LocalTemplateService:
    """Сервис для управления локальными шаблонами"""
    
    @staticmethod
    def create_local_template(name, description, activity_category, created_by, based_on_global=None):
        """
        Создать локальный шаблон
        
        Args:
            name: Название шаблона
            description: Описание шаблона
            activity_category: Объект ActivityCategory
            created_by: Пользователь, создавший шаблон
            based_on_global: Глобальный шаблон, на основе которого создан локальный (опционально)
            
        Returns:
            TaskTemplate: Созданный локальный шаблон
            
        Raises:
            ValidationError: Если данные невалидны
        """
        # Валидация уникальности названия в рамках тенанта
        if TaskTemplate.objects.filter(
            name=name,
            template_type='local',
            is_active=True
        ).exists():
            raise ValidationError(
                {'name': 'Шаблон с таким названием уже существует в этом тенанте'}
            )
        
        # Используем TemplateService для создания
        template = TemplateService.create_template(
            name=name,
            description=description,
            activity_category=activity_category,
            created_by=created_by,
            template_type='local'
        )
        
        # Если основан на глобальном, копируем этапы
        if based_on_global:
            template.based_on_global = based_on_global
            template.save()
            
            # Копируем этапы
            for stage in based_on_global.stages.all():
                TaskTemplateStage.objects.create(
                    template=template,
                    name=stage.name,
                    description=stage.description,
                    estimated_duration_hours=stage.estimated_duration_hours,
                    sequence_number=stage.sequence_number,
                )
        
        return template
    
    @staticmethod
    def update_local_template(template, name=None, description=None, activity_category=None, updated_by=None):
        """
        Обновить локальный шаблон
        
        Args:
            template: Объект TaskTemplate (локальный)
            name: Новое название (опционально)
            description: Новое описание (опционально)
            activity_category: Новая категория (опционально)
            updated_by: Пользователь, обновивший шаблон
            
        Returns:
            TaskTemplate: Обновленный шаблон
            
        Raises:
            ValidationError: Если данные невалидны
        """
        if template.template_type != 'local':
            raise ValidationError('Это не локальный шаблон')
        
        # Проверка уникальности названия
        if name and name != template.name:
            if TaskTemplate.objects.filter(
                name=name,
                template_type='local',
                is_active=True
            ).exclude(id=template.id).exists():
                raise ValidationError(
                    {'name': 'Шаблон с таким названием уже существует в этом тенанте'}
                )
        
        return TemplateService.update_template(
            template=template,
            name=name,
            description=description,
            activity_category=activity_category,
            updated_by=updated_by
        )
    
    @staticmethod
    def delete_local_template(template, deleted_by=None):
        """
        Удалить локальный шаблон
        
        Args:
            template: Объект TaskTemplate (локальный)
            deleted_by: Пользователь, удаливший шаблон
            
        Raises:
            ValidationError: Если это не локальный шаблон
        """
        if template.template_type != 'local':
            raise ValidationError('Это не локальный шаблон')
        
        TemplateService.delete_template(template, deleted_by)


class ProposalService:
    """Сервис для управления предложениями шаблонов"""
    
    @staticmethod
    def create_proposal(local_template, proposed_by):
        """
        Создать предложение шаблона
        
        Args:
            local_template: Объект TaskTemplate (локальный)
            proposed_by: Пользователь, предложивший шаблон
            
        Returns:
            TemplateProposal: Созданное предложение
            
        Raises:
            ValidationError: Если данные невалидны
        """
        if local_template.template_type != 'local':
            raise ValidationError('Можно предлагать только локальные шаблоны')
        
        # Проверка, нет ли уже активного предложения
        existing_proposal = TemplateProposal.objects.filter(
            local_template=local_template,
            status__in=['pending', 'approved']
        ).first()
        
        if existing_proposal:
            raise ValidationError(
                f'Для этого шаблона уже существует предложение со статусом {existing_proposal.get_status_display()}'
            )
        
        with transaction.atomic():
            proposal = TemplateProposal.objects.create(
                local_template=local_template,
                proposed_by_id=proposed_by if isinstance(proposed_by, int) else (proposed_by.id if proposed_by else None),
                status='pending',
            )
            
            # Логирование в аудит
            TemplateAuditLog.objects.create(
                action='create',
                proposal=proposal,
                performed_by_id=proposed_by if isinstance(proposed_by, int) else (proposed_by.id if proposed_by else None),
                changes={
                    'template_name': local_template.name,
                    'status': 'pending',
                }
            )
        
        return proposal
    
    @staticmethod
    def update_proposal(proposal, name=None, description=None, updated_by=None):
        """
        Обновить предложение (только в статусе 'pending')
        
        Args:
            proposal: Объект TemplateProposal
            name: Новое название (опционально)
            description: Новое описание (опционально)
            updated_by: Пользователь, обновивший предложение
            
        Returns:
            TemplateProposal: Обновленное предложение
            
        Raises:
            ValidationError: Если предложение не в статусе 'pending'
        """
        if proposal.status != 'pending':
            raise ValidationError(
                f'Можно редактировать только предложения в статусе "ожидание", текущий статус: {proposal.get_status_display()}'
            )
        
        # Обновляем локальный шаблон
        LocalTemplateService.update_local_template(
            template=proposal.local_template,
            name=name,
            description=description,
            updated_by=updated_by
        )
        
        # Логирование в аудит
        TemplateAuditLog.objects.create(
            action='update',
            proposal=proposal,
            performed_by_id=updated_by if isinstance(updated_by, int) else (updated_by.id if updated_by else None),
            changes={
                'name': name,
                'description': description,
            }
        )
        
        return proposal
    
    @staticmethod
    def withdraw_proposal(proposal, withdrawn_by=None):
        """
        Отозвать предложение (только в статусе 'pending')
        
        Args:
            proposal: Объект TemplateProposal
            withdrawn_by: Пользователь, отозвавший предложение
            
        Raises:
            ValidationError: Если предложение не в статусе 'pending'
        """
        if proposal.status != 'pending':
            raise ValidationError(
                f'Можно отозвать только предложения в статусе "ожидание", текущий статус: {proposal.get_status_display()}'
            )
        
        with transaction.atomic():
            # Логирование в аудит
            TemplateAuditLog.objects.create(
                action='delete',
                proposal=proposal,
                performed_by_id=withdrawn_by if isinstance(withdrawn_by, int) else (withdrawn_by.id if withdrawn_by else None),
                changes={
                    'action': 'withdraw_proposal',
                    'template_name': proposal.local_template.name,
                }
            )
            
            proposal.delete()
    
    @staticmethod
    def approve_proposal(proposal, approved_by):
        """
        Одобрить предложение и создать глобальный шаблон
        
        Args:
            proposal: Объект TemplateProposal
            approved_by: Пользователь (root-администратор), одобривший предложение
            
        Returns:
            TaskTemplate: Созданный глобальный шаблон
            
        Raises:
            ValidationError: Если предложение не в статусе 'pending'
        """
        if proposal.status != 'pending':
            raise ValidationError(
                f'Можно одобрить только предложения в статусе "ожидание", текущий статус: {proposal.get_status_display()}'
            )
        
        with transaction.atomic():
            # Создаем глобальный шаблон на основе локального
            local_template = proposal.local_template
            
            global_template = TaskTemplate.objects.create(
                name=local_template.name,
                description=local_template.description,
                activity_category=local_template.activity_category,
                created_by_id=approved_by if isinstance(approved_by, int) else (approved_by.id if approved_by else None),
                template_type='global',
                version=1,
                is_active=True,
            )
            
            # Копируем этапы
            for stage in local_template.stages.all():
                TaskTemplateStage.objects.create(
                    template=global_template,
                    name=stage.name,
                    description=stage.description,
                    estimated_duration_hours=stage.estimated_duration_hours,
                    sequence_number=stage.sequence_number,
                )
            
            # Обновляем предложение
            proposal.status = 'approved'
            proposal.approved_global_template = global_template
            proposal.reviewed_by_id = approved_by if isinstance(approved_by, int) else (approved_by.id if approved_by else None)
            proposal.reviewed_at = timezone.now()
            proposal.save()
            
            # Логирование в аудит
            TemplateAuditLog.objects.create(
                action='approve_proposal',
                proposal=proposal,
                performed_by_id=approved_by if isinstance(approved_by, int) else (approved_by.id if approved_by else None),
                changes={
                    'template_name': local_template.name,
                    'global_template_id': global_template.id,
                }
            )
        
        return global_template
    
    @staticmethod
    def reject_proposal(proposal, rejection_reason, rejected_by):
        """
        Отклонить предложение
        
        Args:
            proposal: Объект TemplateProposal
            rejection_reason: Причина отклонения
            rejected_by: Пользователь (root-администратор), отклонивший предложение
            
        Raises:
            ValidationError: Если предложение не в статусе 'pending'
        """
        if proposal.status != 'pending':
            raise ValidationError(
                f'Можно отклонить только предложения в статусе "ожидание", текущий статус: {proposal.get_status_display()}'
            )
        
        with transaction.atomic():
            proposal.status = 'rejected'
            proposal.rejection_reason = rejection_reason or ''
            proposal.reviewed_by_id = rejected_by if isinstance(rejected_by, int) else (rejected_by.id if rejected_by else None)
            proposal.reviewed_at = timezone.now()
            proposal.save()
            
            # Логирование в аудит
            TemplateAuditLog.objects.create(
                action='reject_proposal',
                proposal=proposal,
                performed_by_id=rejected_by if isinstance(rejected_by, int) else (rejected_by.id if rejected_by else None),
                changes={
                    'template_name': proposal.local_template.name,
                    'rejection_reason': rejection_reason,
                }
            )


class FilterService:
    """Сервис для управления предпочтениями фильтра"""
    
    @staticmethod
    def get_user_filter_preference(user):
        """
        Получить предпочтение фильтра пользователя
        
        Args:
            user: Объект TenantUser
            
        Returns:
            TemplateFilterPreference: Предпочтение пользователя или None
        """
        return TemplateFilterPreference.objects.filter(user=user).first()
    
    @staticmethod
    def set_filter_preference(user, show_all_categories=False, last_category_filter=None):
        """
        Установить предпочтение фильтра пользователя
        
        Args:
            user: Объект TenantUser
            show_all_categories: Показывать ли все категории
            last_category_filter: Последний выбранный фильтр категории
            
        Returns:
            TemplateFilterPreference: Обновленное предпочтение
        """
        preference, created = TemplateFilterPreference.objects.get_or_create(user=user)
        
        preference.show_all_categories = show_all_categories
        if last_category_filter:
            preference.last_category_filter = last_category_filter
        
        preference.save()
        
        return preference
    
    @staticmethod
    def get_visible_templates(user, tenant_default_category=None):
        """
        Получить видимые шаблоны для пользователя на основе его предпочтений
        
        Args:
            user: Объект TenantUser
            tenant_default_category: Категория по умолчанию для тенанта
            
        Returns:
            QuerySet: Видимые шаблоны (глобальные + локальные)
        """
        preference = FilterService.get_user_filter_preference(user)
        
        # Локальные шаблоны всегда видны
        local_templates = TaskTemplate.objects.filter(
            template_type='local',
            is_active=True
        )
        
        # Глобальные шаблоны в зависимости от предпочтения
        if preference and preference.show_all_categories:
            # Показываем все категории
            global_templates = TaskTemplate.objects.filter(
                template_type='global',
                is_active=True
            )
        else:
            # Показываем только категорию по умолчанию
            category = tenant_default_category
            if preference and preference.last_category_filter:
                category = preference.last_category_filter
            
            if category:
                global_templates = TaskTemplate.objects.filter(
                    template_type='global',
                    activity_category=category,
                    is_active=True
                )
            else:
                global_templates = TaskTemplate.objects.none()
        
        # Объединяем и возвращаем
        from django.db.models import Q
        return TaskTemplate.objects.filter(
            Q(id__in=local_templates) | Q(id__in=global_templates)
        ).prefetch_related('stages')

