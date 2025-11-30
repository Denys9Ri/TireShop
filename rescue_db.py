import os
import django
from django.db import connection

# Налаштування
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TireShop.settings')
django.setup()

print("🚑 Починаю аварійне очищення бази даних...")

with connection.cursor() as cursor:
    # 1. Видаляємо колонку image, яка викликає помилку зараз
    print("- Видаляю колонку image з таблиці фото...")
    cursor.execute("ALTER TABLE store_productimage DROP COLUMN IF EXISTS image;")

    # 2. На всяк випадок видаляємо таблиці, які теж можуть викликати помилку далі
    print("- Видаляю таблицю SiteBanner (щоб створилась наново)...")
    cursor.execute("DROP TABLE IF EXISTS store_sitebanner CASCADE;")
    
    print("- Видаляю таблицю SiteSettings...")
    cursor.execute("DROP TABLE IF EXISTS store_sitesettings CASCADE;")

    # 3. Видаляємо нові колонки з товарів, якщо вони там застрягли
    print("- Чищу нові поля в товарах...")
    columns = ['country', 'year', 'load_index', 'speed_index', 'stud_type', 'vehicle_type', 'discount_percent']
    for col in columns:
        cursor.execute(f"ALTER TABLE store_product DROP COLUMN IF EXISTS {col};")

print("✅ Очищення завершено! Тепер Django зможе створити все сам.")
