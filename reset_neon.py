import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TireShop.settings')
django.setup()

print("☢️ УВАГА! Починаю повне очищення бази даних в Neon...")

with connection.cursor() as cursor:
    # 1. Видаляємо всі наші таблиці (каскадно, щоб не було помилок зв'язків)
    tables = [
        'store_orderitem', 'store_order', 'store_product', 'store_brand', 
        'store_sitebanner', 'store_aboutimage', 'store_sitesettings',
        'django_migrations' # Видаляємо історію міграцій, щоб почати з чистого аркуша
    ]
    
    for table in tables:
        print(f"- Видаляю таблицю {table}...")
        cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")

print("✅ База чиста. Тепер Django створить її наново при деплої.")
