import os
import django
from django.db import connection

# Налаштування
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TireShop.settings')
django.setup()

print("🧹 Починаю очищення конфліктних таблиць та колонок...")

with connection.cursor() as cursor:
    # 1. Видаляємо таблиці, які викликають помилку "already exists"
    print("- Видаляю таблицю SiteBanner...")
    cursor.execute("DROP TABLE IF EXISTS store_sitebanner CASCADE;")
    
    print("- Видаляю таблицю SiteSettings...")
    cursor.execute("DROP TABLE IF EXISTS store_sitesettings CASCADE;")

    # 2. Видаляємо нові колонки з товарів, щоб Django створив їх чисто
    print("- Очищаю нові поля в таблиці Product...")
    # Список нових колонок, які ми додавали
    new_columns = [
        'country', 'year', 'load_index', 'speed_index', 
        'stud_type', 'vehicle_type', 'discount_percent'
    ]
    
    for col in new_columns:
        # SQL команда: видалити колонку, якщо вона існує
        cursor.execute(f"ALTER TABLE store_product DROP COLUMN IF EXISTS {col};")

    # 3. Очищаємо історію міграції про ці зміни (якщо вона там застрягла)
    print("- Коригую історію міграцій...")
    cursor.execute("DELETE FROM django_migrations WHERE app='store' AND name LIKE '%sitebanner%';")
    cursor.execute("DELETE FROM django_migrations WHERE app='store' AND name LIKE '%product_country%';")

print("✅ Очищення завершено! Тепер запускайте звичайний деплой.")
