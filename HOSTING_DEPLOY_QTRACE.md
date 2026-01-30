# Инструкция по развертыванию на qtrace.ru

## Подготовка

### 1. Подключение к серверу
```bash
ssh s1147486@qtrace.ru
```

### 2. Переход в директорию проекта
```bash
cd ~/domains/qtrace.ru/qtrace
```

## Резервное копирование

### Создание резервной копии базы данных
```bash
# Узнайте параметры подключения из .env
cat .env | grep DATABASE

# Создайте резервную копию
pg_dump -h localhost -U your_db_user -d skkp_db > ~/backups/backup_$(date +%Y%m%d_%H%M%S).sql

# Или если нужен пароль:
PGPASSWORD='your_password' pg_dump -h localhost -U your_db_user -d skkp_db > ~/backups/backup_$(date +%Y%m%d_%H%M%S).sql
```

### Создание резервной копии файлов
```bash
cd ~/domains/qtrace.ru
tar -czf ~/backups/qtrace_files_$(date +%Y%m%d_%H%M%S).tar.gz qtrace/
```

## Получение изменений из Git

```bash
cd ~/domains/qtrace.ru/qtrace

# Проверьте текущую ветку
git branch

# Проверьте статус
git status

# Если есть локальные изменения, сохраните их
git stash

# Получите изменения
git fetch origin

# Переключитесь на ветку с исправлениями
git checkout feature/diagram-cytoscape

# Подтяните последние изменения
git pull origin feature/diagram-cytoscape

# Если сохраняли изменения, верните их
# git stash pop
```

## Применение изменений

### 1. Активация виртуального окружения
```bash
source .venv/bin/activate
```

### 2. Проверка и установка зависимостей
```bash
# Проверьте, изменился ли requirements.txt
git diff HEAD~10 requirements.txt

# Если изменился - обновите зависимости
pip install -r requirements.txt
```

### 3. Проверка миграций
```bash
# Проверьте, есть ли непримененные миграции
python manage.py showmigrations | grep "\[ \]"

# Если есть - примените их
python manage.py migrate

# Проверьте, что все применилось
python manage.py showmigrations | grep "\[ \]"
```

### 4. Сборка статических файлов
```bash
# Соберите статические файлы
python manage.py collectstatic --noinput

# Проверьте права доступа
chmod -R 755 staticfiles/
ls -la staticfiles/
```

### 5. Проверка конфигурации
```bash
# Проверьте настройки Django
python manage.py check

# Проверьте, что нет ошибок
python manage.py check --deploy
```

## Перезапуск приложения

### Для Passenger (рекомендуется для shared hosting)
```bash
# Создайте/обновите файл restart.txt
mkdir -p tmp
touch tmp/restart.txt

# Проверьте, что файл создан
ls -la tmp/restart.txt
```

### Альтернатива: перезапуск через панель управления
1. Войдите в панель управления хостингом
2. Найдите раздел "Python приложения" или "Passenger"
3. Нажмите кнопку "Restart"

## Проверка работоспособности

### 1. Проверка логов
```bash
# Проверьте логи Passenger
tail -f ~/logs/passenger.log

# Или логи приложения (если настроены)
tail -f ~/domains/qtrace.ru/qtrace/logs/django.log
```

### 2. Проверка через браузер

1. Откройте https://qtrace.ru
2. Войдите как суперпользователь
3. Перейдите в "Типовые шаблоны" → Редактировать любой шаблон
4. Проверьте:
   - ✅ Материалы отображаются с количеством
   - ✅ Единица измерения - выпадающий список
   - ✅ При выборе материала единица измерения заполняется
   - ✅ Количество сохраняется после редактирования

5. Войдите как администратор тенанта (например, wb.qtrace.ru)
6. Перейдите в "Мои шаблоны" → Редактировать
7. Повторите проверку

### 3. Проверка API endpoints
```bash
# Проверьте, что API работает
curl -I https://qtrace.ru/api/materials/
curl -I https://qtrace.ru/api/units/
curl -I https://qtrace.ru/api/customers/materials/
curl -I https://qtrace.ru/api/customers/units-of-measure/
```

## Откат изменений (если что-то пошло не так)

### 1. Откат кода
```bash
cd ~/domains/qtrace.ru/qtrace

# Найдите хеш коммита до изменений
git log --oneline -20

# Вернитесь к предыдущему коммиту
git checkout <hash-коммита>

# Перезапустите
touch tmp/restart.txt
```

### 2. Откат базы данных (если применяли миграции)
```bash
# Восстановите из резервной копии
PGPASSWORD='your_password' psql -h localhost -U your_db_user -d skkp_db < ~/backups/backup_YYYYMMDD_HHMMSS.sql
```

## Устранение проблем

### Проблема: 500 Internal Server Error
```bash
# Проверьте логи
tail -100 ~/logs/passenger.log

# Проверьте права доступа
ls -la ~/domains/qtrace.ru/qtrace/
chmod -R 755 ~/domains/qtrace.ru/qtrace/staticfiles/

# Проверьте, что виртуальное окружение активно
which python
```

### Проблема: Статические файлы не загружаются
```bash
# Пересоберите статику
source .venv/bin/activate
python manage.py collectstatic --noinput --clear
chmod -R 755 staticfiles/
```

### Проблема: Материалы не отображаются
```bash
# Проверьте, что API работает
curl https://qtrace.ru/api/materials/

# Проверьте логи браузера (F12 → Console)
# Очистите кэш браузера (Ctrl+F5)
```

### Проблема: Ошибка миграций
```bash
# Проверьте статус миграций
python manage.py showmigrations

# Попробуйте применить конкретную миграцию
python manage.py migrate app_name migration_name

# Если не помогает - откатите код и восстановите БД из резервной копии
```

## Контрольный список

- [ ] Создана резервная копия базы данных
- [ ] Создана резервная копия файлов
- [ ] Получены изменения из Git
- [ ] Проверены и применены миграции
- [ ] Собраны статические файлы
- [ ] Перезапущено приложение
- [ ] Проверена работа через браузер (суперпользователь)
- [ ] Проверена работа через браузер (тенант)
- [ ] Проверены логи на наличие ошибок

## Полезные команды

```bash
# Проверка версии Python
python --version

# Проверка установленных пакетов
pip list

# Проверка переменных окружения
env | grep DJANGO

# Проверка процессов
ps aux | grep python

# Проверка использования диска
df -h
du -sh ~/domains/qtrace.ru/qtrace/*

# Очистка старых логов
find ~/logs -name "*.log" -mtime +30 -delete
```

## Контакты

При возникновении проблем:
1. Проверьте логи: `tail -100 ~/logs/passenger.log`
2. Проверьте консоль браузера (F12)
3. Создайте issue в репозитории с описанием проблемы

## Статус развертывания

- Дата: _________________
- Время: _________________
- Выполнил: _________________
- Результат: ☐ Успешно ☐ С ошибками ☐ Откат
- Примечания: _________________
