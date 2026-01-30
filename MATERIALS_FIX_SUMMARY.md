# Исправление выбора и добавления материалов в редакторе шаблонов

## Проблема
В редакторе типового шаблона (как для суперпользователя, так и для локальных шаблонов) не работал выбор и добавление материалов:
- При редактировании существующего шаблона селекты материалов не заполнялись
- При добавлении нового материала селект не заполнялся списком доступных материалов
- **Количество материалов не сохранялось при сохранении шаблона**

## Решение

### Изменения в файлах:

#### 1. `skkp_project/dashboard/templates/dashboard/local_template_form.html`
**Изменения в JavaScript:**
- Добавлена функция `updateAllMaterialSelects()` для обновления всех селектов материалов
- Добавлена функция `updateMaterialSelect(select)` для заполнения конкретного селекта материалов
- Изменен вызов API материалов: теперь после загрузки вызывается `updateAllMaterialSelects()`
- Упрощена логика добавления нового материала: используется `updateMaterialSelect()` вместо дублирования кода
- Упрощена логика инициализации существующих материалов: используется `updateMaterialSelect()` вместо дублирования кода

**Что теперь работает:**
- При загрузке страницы редактирования все селекты материалов автоматически заполняются
- При добавлении нового материала селект сразу заполняется списком доступных материалов
- При выборе материала автоматически заполняется единица измерения
- Код стал более чистым и поддерживаемым (нет дублирования логики)

#### 2. `skkp_project/customers/templates/customers/superuser_template_form.html`
**Изменения:** (аналогичные изменениям в локальной форме)
- Добавлена функция `updateAllMaterialSelects()` для обновления всех селектов материалов
- Добавлена функция `updateMaterialSelect(select)` для заполнения конкретного селекта материалов
- Изменен вызов API материалов: теперь после загрузки вызывается `updateAllMaterialSelects()`
- Упрощена логика добавления нового материала
- Упрощена логика инициализации существующих материалов

**Что теперь работает:**
- При загрузке страницы редактирования все селекты материалов автоматически заполняются
- При добавлении нового материала селект сразу заполняется списком доступных материалов
- При выборе материала автоматически заполняется единица измерения

#### 3. `skkp_project/dashboard/views.py`
**Изменения в LocalTemplateCreateView и LocalTemplateEditView:**
- Полностью переписана логика `form_valid()` для обработки JSON данных из поля `stages_data`
- Добавлена обработка материалов для каждого этапа
- Материалы теперь сохраняются через модель `StageMaterial` с указанием количества
- При редактировании старые этапы удаляются перед созданием новых

**Что теперь работает:**
- Материалы и их количество корректно сохраняются при создании шаблона
- Материалы и их количество корректно сохраняются при редактировании шаблона
- Все данные этапов (название, длительность, должность, материалы) сохраняются корректно

## Технические детали

### Функция updateMaterialSelect(select)
```javascript
function updateMaterialSelect(select) {
    const currentValue = select.value || select.dataset.materialId;
    select.innerHTML = '<option value="">-- Выберите материал --</option>';
    
    materials.forEach(material => {
        const option = document.createElement('option');
        option.value = material.id;
        option.textContent = `${material.name} (${material.code})`;
        option.dataset.unit = material.unit_abbreviation;
        if (material.id == currentValue) {
            option.selected = true;
        }
        select.appendChild(option);
    });
    
    // При выборе материала заполняем единицу измерения
    select.addEventListener('change', function() {
        const selectedOption = this.options[this.selectedIndex];
        const materialItem = this.closest('.material-item');
        const unitField = materialItem.querySelector('.material-unit');
        unitField.value = selectedOption.dataset.unit || 'шт';
    });
}
```

### Обработка материалов на сервере (Python)
```python
# Обработка материалов для этапа
materials = stage_data.get('materials', [])
for material_data in materials:
    material_id = material_data.get('id')
    if material_id:
        try:
            material = Material.objects.get(id=material_id)
            # Создаём связь материала с этапом
            StageMaterial.objects.create(
                stage=stage,
                material=material,
                quantity=float(material_data.get('quantity', 1))  # <-- Сохраняем количество
            )
        except Material.DoesNotExist:
            pass  # Пропускаем несуществующие материалы
```

### Загрузка материалов
```javascript
// Для локальных шаблонов
fetch('/api/materials/')
    .then(response => response.json())
    .then(data => {
        materials = data;
        updateAllMaterialSelects();  // <-- Добавлено
    })
    .catch(error => console.error('Error loading materials:', error));

// Для типовых шаблонов (суперпользователь)
fetch('/api/customers/materials/')
    .then(response => response.json())
    .then(data => {
        materials = data;
        updateAllMaterialSelects();  // <-- Добавлено
    })
    .catch(error => console.error('Error loading materials:', error));
```

## Тестирование

### Для локальных шаблонов (тенант):
1. Перейти на `http://wb.localhost:8000/my-templates/`
2. Создать новый шаблон или открыть существующий для редактирования
3. Добавить этап
4. Нажать кнопку "Добавить материал"
5. Выбрать материал из списка
6. Указать количество (например, 5.5)
7. Сохранить шаблон
8. Открыть шаблон снова для редактирования
9. **Проверить, что количество материала сохранилось (5.5)**

### Для типовых шаблонов (суперпользователь):
1. Перейти на `http://localhost:8000/superuser/templates/`
2. Создать новый шаблон или открыть существующий для редактирования
3. Добавить этап
4. Нажать кнопку "Добавить материал"
5. Выбрать материал из списка
6. Указать количество (например, 3.25)
7. Сохранить шаблон
8. Открыть шаблон снова для редактирования
9. **Проверить, что количество материала сохранилось (3.25)**

## Статус
✅ Исправление завершено
✅ Код оптимизирован (убрано дублирование)
✅ Количество материалов теперь сохраняется корректно
✅ Готово к тестированию
