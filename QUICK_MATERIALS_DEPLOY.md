# Быстрое развертывание исправлений материалов

## Для опытных администраторов

**Важно:** Проверьте непримененные миграции на хостинге!

### 1. Резервная копия (обязательно!)
```bash
cd ~/domains/qtrace.ru/qtrace
pg_dump -U your_db_user -d skkp_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 2. Получение изменений
```bash
git fetch origin
git checkout feature/diagram-cytoscape
git pull origin feature/diagram-cytoscape
```

### 3. Применение
```bash
source .venv/bin/activate
python manage.py showmigrations | grep "\[ \]"  # Проверка непримененных миграций
python manage.py migrate  # Если есть непримененные
python manage.py collectstatic --noinput
chmod -R 755 staticfiles/
```

### 4. Перезапуск
```bash
touch tmp/restart.txt  # Passenger
# или
sudo systemctl restart gunicorn  # Gunicorn
```

### 5. Проверка
- Откройте редактор шаблона
- Проверьте, что количество материалов отображается
- Проверьте, что единица измерения - выпадающий список
- Сохраните и откройте снова - количество должно сохраниться

## Что исправлено
✅ Количество материалов сохраняется  
✅ Единица измерения - выпадающий список  
✅ Автоматическое заполнение единицы измерения  
✅ Корректное отображение при загрузке  

## Откат (если нужно)
```bash
git checkout <предыдущий-коммит>
touch tmp/restart.txt
```

Подробная инструкция: `MATERIALS_DEPLOYMENT.md`
