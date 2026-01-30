"""
Модуль для экспорта и импорта шаблонов задач
"""
import json
from django.core.serializers.json import DjangoJSONEncoder
from .models import TaskTemplate, TaskTemplateStage, ActivityCategory, Material, StageMaterial, DurationUnit, Position


class TemplateExporter:
    """Класс для экспорта шаблонов в JSON"""
    
    @staticmethod
    def export_template(template):
        """
        Экспортирует один шаблон в словарь
        
        Args:
            template: Объект TaskTemplate
            
        Returns:
            dict: Данные шаблона в формате для экспорта
        """
        data = {
            'version': '1.0',
            'template': {
                'name': template.name,
                'description': template.description,
                'template_type': template.template_type,
                'activity_category': template.activity_category.name if template.activity_category else None,
                'diagram_svg': template.diagram_svg,
                'stages': []
            }
        }
        
        # Экспортируем этапы
        for stage in template.stages.all().order_by('sequence_number'):
            stage_data = {
                'name': stage.name,
                'sequence_number': stage.sequence_number,
                'duration_from': float(stage.duration_from) if stage.duration_from else None,
                'duration_to': float(stage.duration_to) if stage.duration_to else None,
                'duration_unit': stage.duration_unit.name if stage.duration_unit else None,
                'position': stage.position.name if stage.position else None,
                'parent_stage_sequence': stage.parent_stage.sequence_number if stage.parent_stage else None,
                'leads_to_stop': stage.leads_to_stop,
                'materials': []
            }
            
            # Экспортируем материалы этапа
            for stage_material in stage.materials.all():
                material_data = {
                    'material_name': stage_material.material.name,
                    'quantity': float(stage_material.quantity) if stage_material.quantity else None,
                    'unit': stage_material.material.unit.name if stage_material.material.unit else None
                }
                stage_data['materials'].append(material_data)
            
            data['template']['stages'].append(stage_data)
        
        return data
    
    @staticmethod
    def export_to_json(template):
        """
        Экспортирует шаблон в JSON строку
        
        Args:
            template: Объект TaskTemplate
            
        Returns:
            str: JSON строка
        """
        data = TemplateExporter.export_template(template)
        return json.dumps(data, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder)
    
    @staticmethod
    def export_multiple_templates(templates):
        """
        Экспортирует несколько шаблонов в один JSON
        
        Args:
            templates: QuerySet или список объектов TaskTemplate
            
        Returns:
            str: JSON строка с массивом шаблонов
        """
        data = {
            'version': '1.0',
            'templates': [TemplateExporter.export_template(t)['template'] for t in templates]
        }
        return json.dumps(data, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder)


class TemplateImporter:
    """Класс для импорта шаблонов из JSON"""
    
    def __init__(self, user=None, tenant=None):
        self.user = user
        self.tenant = tenant
        self.errors = []
        self.warnings = []
        self.created_objects = {
            'templates': [],
            'stages': [],
            'categories': [],
            'materials': [],
            'positions': [],
            'units': []
        }
    
    def import_from_json(self, json_string, template_type='local', conflict_strategy='rename'):
        """
        Импортирует шаблон(ы) из JSON строки
        
        Args:
            json_string: JSON строка с данными шаблона
            template_type: 'local' или 'global'
            conflict_strategy: 'rename', 'skip', 'overwrite'
            
        Returns:
            dict: Результат импорта с информацией о созданных объектах и ошибках
        """
        try:
            data = json.loads(json_string)
        except json.JSONDecodeError as e:
            self.errors.append(f"Ошибка парсинга JSON: {str(e)}")
            return self._get_result()
        
        # Проверяем версию формата
        if data.get('version') != '1.0':
            self.warnings.append(f"Неизвестная версия формата: {data.get('version')}")
        
        # Определяем, один шаблон или несколько
        if 'template' in data:
            # Один шаблон
            self._import_single_template(data['template'], template_type, conflict_strategy)
        elif 'templates' in data:
            # Несколько шаблонов
            for template_data in data['templates']:
                self._import_single_template(template_data, template_type, conflict_strategy)
        else:
            self.errors.append("Неверный формат данных: отсутствует 'template' или 'templates'")
        
        return self._get_result()
    
    def _import_single_template(self, template_data, template_type, conflict_strategy):
        """Импортирует один шаблон"""
        template_name = template_data.get('name')
        
        if not template_name:
            self.errors.append("Отсутствует имя шаблона")
            return
        
        # Проверяем конфликт имен
        existing_template = TaskTemplate.objects.filter(
            name=template_name,
            template_type=template_type
        ).first()
        
        if existing_template:
            if conflict_strategy == 'skip':
                self.warnings.append(f"Шаблон '{template_name}' пропущен (уже существует)")
                return
            elif conflict_strategy == 'rename':
                # Добавляем суффикс к имени
                counter = 1
                new_name = f"{template_name} (копия)"
                while TaskTemplate.objects.filter(name=new_name, template_type=template_type).exists():
                    counter += 1
                    new_name = f"{template_name} (копия {counter})"
                template_name = new_name
                self.warnings.append(f"Шаблон переименован в '{template_name}'")
            elif conflict_strategy == 'overwrite':
                existing_template.delete()
                self.warnings.append(f"Шаблон '{template_name}' перезаписан")
        
        # Получаем или создаем категорию
        category = None
        category_name = template_data.get('activity_category')
        if category_name:
            category, created = ActivityCategory.objects.get_or_create(name=category_name)
            if created:
                self.created_objects['categories'].append(category_name)
        
        # Создаем шаблон
        template = TaskTemplate.objects.create(
            name=template_name,
            description=template_data.get('description', ''),
            template_type=template_type,
            activity_category=category,
            diagram_svg=template_data.get('diagram_svg', '')
        )
        self.created_objects['templates'].append(template_name)
        
        # Импортируем этапы
        stages_map = {}  # Для связывания parent_stage
        
        for stage_data in template_data.get('stages', []):
            stage = self._import_stage(template, stage_data, stages_map)
            if stage:
                stages_map[stage_data.get('sequence_number')] = stage
        
        # Устанавливаем parent_stage связи
        for stage_data in template_data.get('stages', []):
            parent_seq = stage_data.get('parent_stage_sequence')
            if parent_seq and parent_seq in stages_map:
                stage = stages_map.get(stage_data.get('sequence_number'))
                if stage:
                    stage.parent_stage = stages_map[parent_seq]
                    stage.save()
    
    def _import_stage(self, template, stage_data, stages_map):
        """Импортирует один этап"""
        # Получаем или создаем единицу измерения
        duration_unit = None
        unit_name = stage_data.get('duration_unit')
        if unit_name:
            duration_unit, created = DurationUnit.objects.get_or_create(
                name=unit_name,
                defaults={'unit_type': 'time'}
            )
            if created:
                self.created_objects['units'].append(unit_name)
        
        # Получаем или создаем должность
        position = None
        position_name = stage_data.get('position')
        if position_name:
            # Ищем должность по имени (без get_or_create, чтобы избежать проблем со схемами)
            try:
                position = Position.objects.get(name=position_name)
            except Position.DoesNotExist:
                position = Position.objects.create(name=position_name)
                self.created_objects['positions'].append(position_name)
            except Position.MultipleObjectsReturned:
                # Если несколько - берем первую
                position = Position.objects.filter(name=position_name).first()
        
        # Создаем этап
        stage = TaskTemplateStage.objects.create(
            template=template,
            name=stage_data.get('name', ''),
            sequence_number=stage_data.get('sequence_number', 0),
            duration_from=stage_data.get('duration_from'),
            duration_to=stage_data.get('duration_to'),
            duration_unit=duration_unit,
            position=position,
            leads_to_stop=stage_data.get('leads_to_stop', False)
        )
        self.created_objects['stages'].append(stage.name)
        
        # Импортируем материалы этапа
        for material_data in stage_data.get('materials', []):
            self._import_stage_material(stage, material_data)
        
        return stage
    
    def _import_stage_material(self, stage, material_data):
        """Импортирует материал этапа"""
        material_name = material_data.get('material_name')
        if not material_name:
            return
        
        # Получаем или создаем единицу измерения материала
        unit = None
        unit_name = material_data.get('unit')
        if unit_name:
            unit, created = DurationUnit.objects.get_or_create(
                name=unit_name,
                defaults={'unit_type': 'quantity'}
            )
            if created:
                self.created_objects['units'].append(unit_name)
        
        # Получаем или создаем материал
        material, created = Material.objects.get_or_create(
            name=material_name,
            defaults={'unit': unit}
        )
        if created:
            self.created_objects['materials'].append(material_name)
        
        # Создаем связь материала с этапом
        StageMaterial.objects.create(
            stage=stage,
            material=material,
            quantity=material_data.get('quantity')
        )
    
    def _get_result(self):
        """Возвращает результат импорта"""
        return {
            'success': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'created': self.created_objects
        }
