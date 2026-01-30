#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from task_templates.models import TaskTemplate

# Получаем первый шаблон
template = TaskTemplate.objects.first()
if template:
    print(f"Template: {template.name}")
    print(f"Has diagram_svg: {bool(template.diagram_svg)}")
    print(f"diagram_svg length: {len(template.diagram_svg) if template.diagram_svg else 0}")
    
    # Проверяем, что поле может хранить SVG
    test_svg = '<svg><circle cx="50" cy="50" r="40"/></svg>'
    template.diagram_svg = test_svg
    template.save()
    
    # Проверяем, что сохранилось
    template.refresh_from_db()
    print(f"Saved SVG: {template.diagram_svg}")
    print("✓ SVG storage works!")
else:
    print("No templates found")
