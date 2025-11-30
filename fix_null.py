import os
import django
from django.db import connection

# Налаштовуємо Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TireShop.settings')
django.setup()

print("🛠 Виправляю таблицю: роблю image_url необов'язковим...")

with connection.cursor() as cursor:
    # Ця команда каже базі: "Дозволь зберігати пустоту (NULL) в колонці image_url"
    cursor.execute('''
        ALTER TABLE store_productimage 
        ALTER COLUMN image_url DROP NOT NULL;
    ''')

print("✅ Готово! Тепер можна додавати тільки фото, без посилання.")
