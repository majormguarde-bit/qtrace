# Полная инструкция по развертыванию на хостинге

## Обзор изменений

Ветка `feature/diagram-cytoscape` содержит множество улучшений:
- Диаграммы Cytoscape для визуализации шаблонов
- Экспорт/импорт шаблонов в формате .tpl
- Исправления UI (компактное меню, иконки)
- **Полная поддержка материалов в редакторе шаблонов**
- Множество миграций базы данных

## Важные миграции в ветке

### task_templates:
- `0003_material_stagematerial` - добавлены материалы и связь с этапами
- `0004_durationunit_unitofmeasure_and_more` - единицы измерения
- `0005_alter_durationunit_unit_type` - типы единиц времени
- `0006_populate_duration_units` - заполнение единиц времени
- `0007_add_position_and_update_stages` - должности
- `0008_populate_positions` - заполнение должностей
- `0009_remove_executor_name` - удаление старого поля
- `0010_add_parent_stage` - иерархия этапов
- `0011_add_leads_to_stop` - флаг завершения
- `0012_alter_tasktemplatestage_duration_from_and_more` - изменение полей длительности
- `0013_tasktemplate_diagram_svg` - хранение SVG диаграмм

### customers:
- `0014_userprofile` - профили пользователей
- `0015_client_can_admin_delete_media` - права на удаление медиа
- `0016_userprofile_tenant` - связь профиля с тенантом
- `0017-0022` - различные улучшения

### media_app:
- `0005_media_file_size` - размер файла

## Пошаговая инструкция развертывания

### Шаг 1: Резервное копирование (ОБЯЗАТЕЛЬНО!)

```bash
# Подключитесь к серверу
ssh user@your-server.com

# Перейдите в директорию проекта
cd /path/to/skkp_project

# Создайте резервную копию базы данных
pg_dump -U postgres -d skkp_db -F c -f backup_$(date +%Y%m%d_%H%M%S).dump

# Создайте резервную копию файлов
tar -czf backup_files_$(date +%Y%m%d_%H%M%S).tar.gz \
  --exclude='venv' \
  --exclude='venv_new' \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  .
```

### Шаг 2: Получение изменений из GitHub

```bash
# Проверьте текущую ветку
git branch

# Сохраните локальные изменения (если есть)
git stash

# Получите последние изменения
git fetch origin

# Переключитесь на ветку с изменениями
git checkout feature/diagram-cytoscape

# Подтяните изменения
git pull origin feature/diagram-cytoscape
```

### Шаг 3: Обновление зависимостей

```bash
# Активируйте виртуальное окружение
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Обновите pip
pip install --upgrade pip

# Установите/обновите зависимости
pip install -r requirements.txt
```

### Шаг 4: Применение миграций базы данных

```bash
# Проверьте, какие миграции нужно применить
python manage.py showmigrations

# Примените все миграции
python manage.py migrate

# Проверьте, что все миграции применены
python manage.py showmigrations | grep "\[ \]"
# Если вывод пустой - все миграции применены
```

### Шаг 5: Сбор статических файлов

```bash
# Соберите статические файлы
python manage.py collectstatic --noinput

# Проверьте права доступа
chmod -R 755 staticfiles/
```

### Шаг 6: Перезапуск приложения

#### Для Passenger (рекомендуется для shared hosting)

```bash
# Создайте/обновите файл restart.txt
mkdir -p tmp
touch tmp/restart.txt

# Проверьте логи
tail -f passenger_debug.log
```

#### Для Gunicorn

```bash
# Перезапустите сервис
sudo systemctl restart gunicorn

# Проверьте статус
sudo systemctl status gunicorn

# Проверьте логи
sudo journalctl -u gunicorn -f
```

#### Для uWSGI

```bash
# Перезапустите сервис
sudo systemctl restart uwsgi

# Проверьте статус
sudo systemctl status uwsgi
```

#### Для Nginx (если используется)

```bash
# Проверьте конфигурацию
sudo nginx -t

# Перезагрузите Nginx
sudo systemctl reload nginx
```

### Шаг 7: Проверка работоспособности

#### 7.1 Проверка базовой функциональности

```bash
# Проверьте, что сайт доступен
curl -I https://your-domain.com

# Проверьте логи на ошибки
tail -100 /path/to/logs/error.log
```

#### 7.2 Проверка материалов в шаблонах

1. Откройте браузер и перейдите на сайт
2. Войдите как суперпользователь
3. Перейдите в "Типовые шаблоны" → Редактировать шаблон
4. Проверьте:
   - ✅ Материалы отображаются с правильным количеством
   - ✅ Единица измерения - выпадающий список
   - ✅ При выборе материала единица измерения заполняется автоматически
5. Добавьте новый материал с количеством 5.5
6. Сохраните шаблон
7. Откройте снова - количество должно быть 5.5

#### 7.3 Проверка для тенантов

1. Войдите как администратор тенанта
2. Перейдите в "Мои шаблоны"
3. Повторите проверку из п. 7.2

#### 7.4 Проверка экспорта/импорта

1. Экспортируйте шаблон - должен скачаться файл .tpl
2. Импортируйте шаблон - должен создаться новый шаблон

#### 7.5 Проверка диаграмм

1. Откройте шаблон
2. Нажмите "Редактор диаграммы"
3. Проверьте, что диаграмма отображается корректно

### Шаг 8: Мониторинг после развертывания

```bash
# Следите за логами в течение 10-15 минут
tail -f /path/to/logs/error.log

# Проверьте использование ресурсов
top
htop

# Проверьте подключения к базе данных
psql -U postgres -d skkp_db -c "SELECT count(*) FROM pg_stat_activity;"
```

## Откат изменений (если что-то пошло не так)

### Вариант 1: Откат через Git

```bash
# Найдите хеш коммита до изменений
git log --oneline -20

# Вернитесь к предыдущему коммиту
git checkout <hash-коммита>

# Откатите миграции (если нужно)
python manage.py migrate task_templates 0002
python manage.py migrate customers 0013

# Перезапустите сервер
touch tmp/restart.txt
```

### Вариант 2: Восстановление из резервной копии

```bash
# Остановите приложение
# (для Passenger не требуется)

# Восстановите базу данных
pg_restore -U postgres -d skkp_db -c backup_YYYYMMDD_HHMMSS.dump

# Восстановите файлы
tar -xzf backup_files_YYYYMMDD_HHMMSS.tar.gz

# Перезапустите сервер
touch tmp/restart.txt
```

## Возможные проблемы и решения

### Проблема: Ошибка при применении миграций

```
django.db.utils.ProgrammingError: relation "..." already exists
```

**Решение:**
```bash
# Пометьте миграцию как примененную без выполнения
python manage.py migrate --fake <app_name> <migration_name>
```

### Проблема: Статические файлы не обновляются

**Решение:**
```bash
# Очистите старые статические файлы
rm -rf staticfiles/*

# Соберите заново
python manage.py collectstatic --noinput --clear

# Очистите кэш браузера (Ctrl+F5)
```

### Проблема: 500 ошибка после развертывания

**Решение:**
```bash
# Проверьте логи
tail -100 /path/to/logs/error.log

# Проверьте права доступа
ls -la

# Проверьте настройки DEBUG в settings.py
# (должен быть DEBUG = False на продакшене)
```

### Проблема: Материалы не отображаются

**Решение:**
1. Очистите кэш браузера (Ctrl+Shift+Delete)
2. Проверьте консоль браузера (F12) на ошибки JavaScript
3. Проверьте, что API доступны:
   - `/api/materials/`
   - `/api/units/`
   - `/api/customers/materials/`
   - `/api/customers/units-of-measure/`

## Контрольный список

- [ ] Создана резервная копия базы данных
- [ ] Создана резервная копия файлов
- [ ] Получены изменения из GitHub
- [ ] Обновлены зависимости
- [ ] Применены миграции
- [ ] Собраны статические файлы
- [ ] Перезапущен сервер
- [ ] Проверена работа материалов в типовых шаблонах
- [ ] Проверена работа материалов в локальных шаблонах
- [ ] Проверен экспорт/импорт шаблонов
- [ ] Проверены диаграммы
- [ ] Мониторинг логов в течение 15 минут

## Контакты для поддержки

При возникновении проблем:
1. Проверьте логи сервера и браузера
2. Создайте issue на GitHub с описанием проблемы
3. Приложите скриншоты и логи

## Дополнительные ресурсы

- Репозиторий: https://github.com/majormguarde-bit/qtrace.git
- Ветка: `feature/diagram-cytoscape`
- Краткая инструкция: `QUICK_MATERIALS_DEPLOY.md`
- Описание исправлений: `MATERIALS_FIX_SUMMARY.md`
