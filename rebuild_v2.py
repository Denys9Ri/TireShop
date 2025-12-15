import os
import django
from django.core.management import call_command
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TireShop.settings')
django.setup()

print("☢️ ОНОВЛЕННЯ БАЗИ ПІД SEO...")
with connection.cursor() as cursor:
    cursor.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")

call_command('makemigrations', 'store')
call_command('migrate')

from django.contrib.auth.models import User
User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
print("✅ Готово! Можна заливати товари.")
