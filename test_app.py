import os
import sys

# Пути
sys.path.insert(0, '/home/s1147486/domains/qtrace.ru')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

try:
    from config.wsgi import application
    print("✅ Успех: WSGI приложение импортировано без ошибок!")
except Exception as e:
    print("❌ ОШИБКА ПРИ ЗАПУСКЕ:")
    import traceback
    traceback.print_exc()
