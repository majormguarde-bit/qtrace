import os
import sys

# Путь к проекту
project_path = '/home/s1147486/domains/qtrace.ru'
sys.path.insert(0, project_path)

# Путь к библиотекам вашего venv
# Проверьте, что версия именно 3.13 в папке venv/lib/
venv_lib = os.path.join(project_path, 'venv/lib/python3.13/site-packages')
sys.path.insert(0, venv_lib)

# Настройка Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

from config.wsgi import application
