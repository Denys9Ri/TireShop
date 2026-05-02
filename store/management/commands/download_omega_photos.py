import os
import requests
from django.core.management.base import BaseCommand
from store.models import Product
from django.core.files.base import ContentFile
from django.conf import settings

class Command(BaseCommand):
    help = 'Точкове завантаження відсутніх фото'

    def handle(self, *args, **options):
        # 1. Очищаємо описи Ovation (щоб прибрати Nexen), це безпечно
        self.stdout.write("🧹 Чистимо описи для Ovation...")
        Product.objects.filter(name__icontains='Ovation', description__icontains='Nexen').update(description="")

        # 2. Шукаємо товари, де є посилання, але треба перевірити файл
        products = Product.objects.filter(photo_url__isnull=False).exclude(photo_url='')
        
        self.stdout.write(self.style.WARNING(f"🔎 Перевірка файлів для {products.count()} позицій..."))

        headers = {'User-Agent': 'Mozilla/5.0'}
        count_fixed = 0

        for product in products:
            # Перевіряємо: чи пусте поле фото АБО чи файл фізично відсутній на диску
            file_exists = False
            if product.photo:
                file_path = os.path.join(settings.MEDIA_ROOT, str(product.photo))
                file_exists = os.path.exists(file_path)

            if not product.photo or not file_exists:
                try:
                    # Качаємо тільки якщо реально немає файлу
                    res = requests.get(product.photo_url, headers=headers, timeout=10)
                    if res.status_code == 200:
                        # Даємо нове ім'я, щоб уникнути конфліктів
                        ext = product.photo_url.split('.')[-1][:3]
                        filename = f"fixed_{product.id}.{ext}"
                        
                        product.photo.save(filename, ContentFile(res.content), save=True)
                        count_fixed += 1
                        self.stdout.write(self.style.SUCCESS(f"✅ Відновлено фото: {product.name}"))
                except:
                    continue

        self.stdout.write(self.style.SUCCESS(f"🎉 Готово! Відновлено {count_fixed} відсутніх зображень."))
