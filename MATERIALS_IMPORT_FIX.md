# Исправление ошибки импорта материалов

## Проблема

При импорте шаблонов на хостинге возникала ошибка:

```
ValueError: Cannot assign "<DurationUnit: Упаковка ()>": "Material.unit" must be a "UnitOfMeasure" instance.
```

**Причина**: В методе `_import_stage_material()` файла `task_templates/export_import.py` использовалась неправильная модель для единиц измерения материалов.

## Различие между моделями

В системе есть ДВЕ разные модели для единиц измерения:

1. **`DurationUnit`** - для измерения ВРЕМЕНИ (секунды, минуты, часы, дни, годы)
   - Используется в поле `TaskTemplateStage.duration_unit`
   - Хранится в таблице `duration_units`

2. **`UnitOfMeasure`** - для измерения МАТЕРИАЛОВ (штуки, кг, метры, литры и т.д.)
   - Используется в поле `Material.unit`
   - Хранится в таблице `units_of_measure`

## Что было исправлено

### Файл: `task_templates/export_import.py`

#### Было (НЕПРАВИЛЬНО):
```python
def _import_stage_material(self, stage, material_data):
    # ...
    unit, created = DurationUnit.objects.get_or_create(  # ❌ ОШИБКА!
        name=unit_name,
        defaults={'unit_type': 'quantity'}
    )
    # ...
    material, created = Material.objects.get_or_create(
        name=material_name,
        defaults={'unit': unit}  # ❌ Присваивает DurationUnit вместо UnitOfMeasure
    )
```

#### Стало (ПРАВИЛЬНО):
```python
def _import_stage_material(self, stage, material_data):
    # ...
    unit, created = UnitOfMeasure.objects.get_or_create(  # ✅ ПРАВИЛЬНО!
        name=unit_name,
        defaults={'abbreviation': unit_name[:10]}
    )
    # ...
    # Используем try/except вместо get_or_create для лучшей обработки
    try:
        material = Material.objects.get(name=material_name)
    except Material.DoesNotExist:
        # Создаем с обязательными полями code и unit_cost
        material = Material.objects.create(
            name=material_name,
            code=f"MAT-{uuid.uuid4().hex[:8].upper()}",
            unit=unit,  # ✅ Теперь это UnitOfMeasure
            unit_cost=0.00
        )
```

## Дополнительные улучшения

1. **Обработка обязательных полей Material**:
   - `code` - генерируется автоматически (MAT-XXXXXXXX)
   - `unit_cost` - устанавливается в 0.00 по умолчанию
   - `unit` - если не указана, используется "Штука" по умолчанию

2. **Улучшенная обработка ошибок**:
   - Используется `try/except` вместо `get_or_create`
   - Обрабатывается случай `MultipleObjectsReturned`
   - Добавлены значения по умолчанию для quantity

3. **Добавлен импорт**:
   ```python
   from .models import UnitOfMeasure  # Добавлено в импорты
   ```

## Развертывание на хостинге

```bash
# 1. Подключаемся к серверу
ssh s1147486@qtrace.ru

# 2. Переходим в директорию проекта
cd ~/domains/qtrace.ru/qtrace

# 3. Активируем виртуальное окружение
source .venv/bin/activate

# 4. Получаем последние изменения
git fetch origin
git checkout feature/diagram-cytoscape
git pull origin feature/diagram-cytoscape

# 5. Миграции НЕ НУЖНЫ (модели не изменялись, только логика импорта)

# 6. Перезапускаем приложение
touch tmp/restart.txt

# 7. Проверяем логи
tail -f ~/logs/qtrace.ru/error.log
```

## Проверка исправления

1. Войдите в систему как суперпользователь
2. Перейдите в "Типовые шаблоны"
3. Экспортируйте любой шаблон с материалами (кнопка "Экспорт")
4. Импортируйте этот же шаблон обратно (кнопка "Импорт")
5. **Результат**: Импорт должен пройти успешно без ошибки ValueError

## Коммит

```
commit 3b47426
Author: [Your Name]
Date: [Date]

Fix: Исправлена ошибка импорта материалов - используем UnitOfMeasure вместо DurationUnit

- Заменен DurationUnit на UnitOfMeasure в методе _import_stage_material()
- Добавлена обработка обязательных полей Material (code, unit_cost)
- Улучшена обработка ошибок при создании материалов
- Добавлено значение по умолчанию для unit (Штука)
```

## Связанные файлы

- `task_templates/export_import.py` - основное исправление
- `task_templates/models.py` - определения моделей UnitOfMeasure и DurationUnit
- `dashboard/views.py` - использует правильные модели для API
- `customers/views.py` - использует правильные модели для API

## Важно

Это исправление **критически важно** для работы функции импорта шаблонов. Без него импорт любых шаблонов с материалами будет завершаться ошибкой.

Исправление **обратно совместимо** - не требует изменений в базе данных или существующих данных.
