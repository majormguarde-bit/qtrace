Основные команды управления
Миграции:

python manage.py makemigrations                    # Создать миграции
python manage.py migrate_schemas --shared          # Применить миграции к public schema
python manage.py migrate_schemas                   # Применить миграции ко всем тенантам
Работа с тенантами:

python manage.py shell                             # Открыть Django shell для создания клиентов
python manage.py tenant_command <command>          # Выполнить команду для конкретного тенанта
Сервер разработки:

python manage.py runserver 0.0.0.0:8000           # Запустить dev сервер
python manage.py runserver 127.0.0.1:8000         # Запустить локально
Admin интерфейс:

python manage.py createsuperuser                   # Создать суперпользователя
Примеры использования в shell
from customers.models import Client, Domain

# Создать клиента
client = Client.objects.create(name='Tenant 1')

# Создать домен
Domain.objects.create(
    domain='tenant1.localhost',
    tenant=client,
    is_primary=True
)

# Просмотреть всех клиентов
Client.objects.all()
Диагностика
python manage.py check                             # Проверить конфигурацию проекта
python manage.py showmigrations                    # Показать статус миграций
python manage.py dbshell                           # Подключиться к БД напрямую
Для работы с тестами
python manage.py test                              # Запустить все тесты
python manage.py test customers                    # Запустить тесты приложения
Важно: Перед выполнением команд убедись, что:

Виртуальное окружение активировано: .\venv\Scripts\activate
PostgreSQL запущен и доступен
Переменные в .env корректны

-------------------------------------------

python manage.py shell -c "
from customers.models import Client, Domain

# Создать второго клиента
client2 = Client.objects.create(name='Tenant 2')
print(f'Клиент создан: {client2.name} (ID: {client2.id})')

# Создать домены для второго клиента
Domain.objects.create(
    domain='tenant2.localhost',
    tenant=client2,
    is_primary=True
)
print('Домен tenant2.localhost создан')

# Показать всех клиентов и их домены
print('\\nВсе клиенты и домены:')
for client in Client.objects.all():
    print(f'\\n{client.name} (ID: {client.id}):')
    for domain in client.domain_set.all():
        print(f'  - {domain.domain}')
"