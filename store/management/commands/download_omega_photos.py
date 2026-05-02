import os
import requests
from django.core.management.base import BaseCommand
from store.models import Product
from django.core.files.base import ContentFile

class Command(BaseCommand):
    help = 'Безкоштовне завантаження фото прямо з серверів Омеги'

    def handle(self, *args, **options):
        # Беремо товари, де є посилання, але ще немає фізичного файлу фото
        products = Product.objects.filter(photo_url__isnull=False).exclude(photo_url='')
        
        # Відфільтровуємо ті, у яких вже є завантажене фото (щоб не качати по колу)
        products_to_download = [p for p in products if not p.photo]

        self.stdout.write(self.style.WARNING(f"🚀 Знайдено {len(products_to_download)} товарів для завантаження фото..."))

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        count = 0
        for product in products_to_download:
            try:
                self.stdout.write(f"📥 Качаємо для: {product.name}...")
                
                response = requests.get(product.photo_url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    # Генеруємо назву файлу на основі ID або імені
                    ext = product.photo_url.split('.')[-1].split('?')[0] # дістаємо розширення (jpg/png)
                    if len(ext) > 4: ext = 'jpg'
                    
                    filename = f"product_{product.id}.{ext}"
                    
                    # Зберігаємо файл у поле photo
                    product.photo.save(filename, ContentFile(response.content), save=True)
                    count += 1
                else:
                    self.stdout.write(self.style.ERROR(f"❌ Помилка {response.status_code} для {product.photo_url}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"💥 Помилка завантаження: {e}"))

        self.stdout.write(self.style.SUCCESS(f"✅ Готово! Завантажено {count} нових фотографій."))
