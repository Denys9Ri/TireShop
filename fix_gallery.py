import os
import django
from django.db import connection

# Налаштовуємо Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TireShop.settings')
django.setup()

print("🛠 Додаю колонку 'image' в таблицю галереї...")

with connection.cursor() as cursor:
    # SQL-команда, яка вручну додає пропущену колонку
    cursor.execute('''
        ALTER TABLE store_productimage 
        ADD COLUMN IF NOT EXISTS image varchar(100);
    ''')

print("✅ Колонку успішно додано! Можна користуватися.")
