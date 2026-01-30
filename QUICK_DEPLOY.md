# Быстрое развертывание изменений

## Краткая инструкция для опытных администраторов

```bash
# 1. Подключение к серверу
ssh username@your-server.com

# 2. Переход в директорию проекта
cd /path/to/skkp_project

# 3. Резервная копия (ОБЯЗАТЕЛЬНО!)
pg_dump -U postgres -d skkp_db > ~/backup_$(date +%Y%m%d_%H%M%S).sql

# 4. Получение изменений
git fetch origin
git checkout feature/diagram-cytoscape
git pull origin feature/diagram-cytoscape

# 5. Активация виртуального окружения
source venv/bin/activate

# 6. Обновление зависимостей (если нужно)
pip install -r requirements.txt

# 7. Миграции (для проверки)
python manage.py migrate

# 8. Сбор статики
python manage.py collectstatic --noinput

# 9. Проверка
python manage.py check

# 10. Перезапуск (выберите нужный вариант)

# Для Passenger:
touch tmp/restart.txt

# Для Gunicorn:
sudo systemctl restart gunicorn

# Для uWSGI:
sudo systemctl restart uwsgi

# 11. Проверка логов
tail -f /path/to/logs/error.log
```

## Что изменилось

- Компактное меню (padding: 6px вместо 8-10px)
- Светлые заголовки разделов меню
- Темные иконки в таблицах
- По умолчанию "Мои шаблоны" вместо "Типовых"
- Убран столбец "Статус предложения"

## Откат (если нужно)

```bash
git reset --hard HEAD~1
touch tmp/restart.txt  # или sudo systemctl restart gunicorn
```

## Проверка

1. Откройте `https://your-domain.com/` - должен быть лендинг
2. Откройте `https://tenant.your-domain.com/my-templates/` - должны быть "Мои шаблоны"
3. Проверьте меню - должно быть компактным
4. Проверьте иконки - должны быть темными

---

**Коммит**: 6042d6e  
**Время развертывания**: ~2 минуты
