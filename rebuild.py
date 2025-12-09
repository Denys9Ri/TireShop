import os
import django
from django.core.management import call_command
from django.db import connection

# Налаштування
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TireShop.settings')
django.setup()

print("☢️ ЗАПУСК ПОВНОГО ПЕРЕЗАВАНТАЖЕННЯ БАЗИ ДАНИХ...")

# 1. ПОВНЕ ОЧИЩЕННЯ (Зносимо все під нуль)
print("🧹 Очищаю схему бази даних...")
with connection.cursor() as cursor:
    cursor.execute("DROP SCHEMA public CASCADE;")
    cursor.execute("CREATE SCHEMA public;")

# 2. СТВОРЕННЯ МІГРАЦІЙ І ТАБЛИЦЬ
print("🔨 Створюю нові міграції та таблиці...")
# Робимо міграції для всіх додатків
try:
    call_command('makemigrations', 'store', 'users')
    call_command('makemigrations')
    call_command('migrate')
    print("✅ Таблиці успішно створено!")
except Exception as e:
    print(f"❌ Помилка міграції: {e}")

# 3. СТВОРЕННЯ СУПЕРЮЗЕРА (АДМІНА)
print("👤 Створюю Адміна...")
from django.contrib.auth.models import User
try:
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("✅ Адмін створений: Логін 'admin', Пароль 'admin123'")
    else:
        print("ℹ️ Адмін вже існує.")
except Exception as e:
    print(f"⚠️ Не вдалося створити адміна: {e}")

print("🏁 ПЕРЕЗАВАНТАЖЕННЯ ЗАВЕРШЕНО! Сайт готовий до роботи.")
