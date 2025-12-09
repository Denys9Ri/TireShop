import os
import django
from django.db import connection

# Налаштування
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TireShop.settings')
django.setup()

print("🚑 Лагоджу таблицю Брендів (додаю пропущені колонки)...")

with connection.cursor() as cursor:
    # 1. Додаємо колонку country
    print("- Додаю колонку 'country'...")
    try:
        cursor.execute("ALTER TABLE store_brand ADD COLUMN IF NOT EXISTS country varchar(100);")
        print("  OK.")
    except Exception as e:
        print(f"  Помилка: {e}")

    # 2. Додаємо колонку category (для Бота)
    print("- Додаю колонку 'category'...")
    try:
        cursor.execute("ALTER TABLE store_brand ADD COLUMN IF NOT EXISTS category varchar(20) DEFAULT 'budget';")
        print("  OK.")
    except Exception as e:
        print(f"  Помилка: {e}")

print("✅ Готово! База даних відповідає коду.")
