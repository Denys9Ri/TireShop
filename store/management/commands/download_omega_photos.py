import os
import requests
from django.core.management.base import BaseCommand
from store.models import Product
from django.core.files.base import ContentFile

class Command(BaseCommand):
    help = 'Примусове завантаження фото з Омеги за прямими посиланнями'

    def handle(self, *args, **options):
        # Беремо всі товари, у яких є URL фото від Омеги
        products = Product.objects.filter(photo_url__isnull=False).exclude(photo_url='')
        
        self.stdout.write(self.style.WARNING(f"🔎 Аналізуємо {products.count()} товарів на наявність фото..."))

        count = 0
        for product in products:
            # ПЕРЕВІРКА: чи є фізичний файл на сервері?
            # Якщо файлу немає, або поле порожнє - качаємо
            if not product.photo or not os.path.exists(product.photo.path):
                try:
                    self.stdout.write(f"📥 Завантаження для: {product.name}")
                    
                    response = requests.get(product.photo_url, timeout=10)
                    
                    if response.status_code == 200:
                        # Формуємо чисте ім'я файлу
                        filename = f"tire_{product.id}.jpg"
                        
                        # Зберігаємо файл
                        product.photo.save(filename, ContentFile(response.content), save=True)
                        count += 1
                        
                        if count % 10 == 0:
                            self.stdout.write(self.style.SUCCESS(f"✅ Вже завантажено {count}..."))
                    else:
                        self.stdout.write(self.style.ERROR(f"⚠️ Омега повернула статус {response.status_code}"))

                except Exception as e:
                    # Якщо виникла помилка (наприклад, шлях .path не знайдено для порожнього поля)
                    # просто пробуємо скачати
                    try:
                        response = requests.get(product.photo_url, timeout=10)
                        if response.status_code == 200:
                            product.photo.save(f"tire_{product.id}.jpg", ContentFile(response.content), save=True)
                            count += 1
                    except:
                        continue

        self.stdout.write(self.style.SUCCESS(f"\n🎉 Роботу завершено!"))
        self.stdout.write(self.style.SUCCESS(f"📸 Завантажено нових фото: {count}"))
