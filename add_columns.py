import os
import django
from django.db import connection

# Налаштування
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TireShop.settings')
django.setup()

print("🔧 Примусово додаю пропущені колонки в таблицю товарів...")

with connection.cursor() as cursor:
    # Список команд для додавання всіх нових полів
    commands = [
        "ALTER TABLE store_product ADD COLUMN IF NOT EXISTS country varchar(50);",
        "ALTER TABLE store_product ADD COLUMN IF NOT EXISTS year integer DEFAULT 2024;",
        "ALTER TABLE store_product ADD COLUMN IF NOT EXISTS load_index varchar(50);",
        "ALTER TABLE store_product ADD COLUMN IF NOT EXISTS speed_index varchar(50);",
        "ALTER TABLE store_product ADD COLUMN IF NOT EXISTS stud_type varchar(50) DEFAULT 'Не шип';",
        "ALTER TABLE store_product ADD COLUMN IF NOT EXISTS vehicle_type varchar(50) DEFAULT 'Легковий';",
        "ALTER TABLE store_product ADD COLUMN IF NOT EXISTS discount_percent integer DEFAULT 0;"
    ]

    for sql in commands:
        try:
            cursor.execute(sql)
            print(f"✅ Виконано: {sql}")
        except Exception as e:
            print(f"⚠️ Вже є або помилка: {e}")

print("🎉 База даних відремонтована! Сайт має працювати.")
