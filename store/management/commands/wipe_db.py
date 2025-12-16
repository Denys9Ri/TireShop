from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'ПОВНЕ ОЧИЩЕННЯ БАЗИ ДАНИХ (Видаляє всі таблиці)'

    def handle(self, *args, **options):
        self.stdout.write("Починаємо очищення бази даних...")
        with connection.cursor() as cursor:
            # Ця команда жорстко видаляє схему public і створює нову
            cursor.execute("DROP SCHEMA public CASCADE;")
            cursor.execute("CREATE SCHEMA public;")
        self.stdout.write(self.style.SUCCESS("✅ БАЗА ДАНИХ ПОВНІСТЮ ОЧИЩЕНА!"))
