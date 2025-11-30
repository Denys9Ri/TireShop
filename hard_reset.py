import os
import django
from django.db import connection

# Налаштування
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TireShop.settings')
django.setup()

print("🧹 Починаю глибоке очищення конфліктів...")

with connection.cursor() as cursor:
    # 1. Видаляємо таблиці, через які сварка
    print("- Видаляю таблицю банерів...")
    cursor.execute("DROP TABLE IF EXISTS store_sitebanner CASCADE;")
    
    print("- Видаляю таблицю налаштувань...")
    cursor.execute("DROP TABLE IF EXISTS store_sitesettings CASCADE;")

    # 2. Видаляємо нові колонки з товарів (щоб Django створив їх сам чисто)
    print("- Очищаю нові поля в товарах...")
    columns = ['country', 'year', 'load_index', 'speed_index', 'stud_type', 'vehicle_type', 'discount_percent']
    for col in columns:
        cursor.execute(f"ALTER TABLE store_product DROP COLUMN IF EXISTS {col};")

    # 3. Видаляємо запис про міграцію (якщо він там криво записався)
    print("- Чищу історію міграцій...")
    cursor.execute("DELETE FROM django_migrations WHERE app='store' AND name='0007_sitebanner_sitesettings_product_country_and_more';")

print("✅ Очищення завершено! Тепер запускайте стандартний migrate.")
