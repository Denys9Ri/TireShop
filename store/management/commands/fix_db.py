from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Видаляє конфліктну таблицю store_aboutimage'

    def handle(self, *args, **kwargs):
        self.stdout.write("Починаємо очистку бази від конфліктів...")
        with connection.cursor() as cursor:
            # Ця команда видаляє ТІЛЬКИ таблицю з картинками "Про нас", яка викликає помилку
            cursor.execute("DROP TABLE IF EXISTS store_aboutimage CASCADE;")
        self.stdout.write(self.style.SUCCESS("✅ Таблицю store_aboutimage успішно видалено!"))
