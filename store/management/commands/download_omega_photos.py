import os
import requests
from django.core.management.base import BaseCommand
from store.models import Product
from django.core.files.base import ContentFile

class Command(BaseCommand):
    help = 'Фінальне шліфування: чистка описів та примусове скачування фото'

    def handle(self, *args, **options):
        # 1. ЧИСТКА ОПИСІВ (Видаляємо згадки про Nexen у інших брендів)
        self.stdout.write("🧹 Очищення старих описів...")
        wrong_desc = Product.objects.exclude(name__icontains='Nexen').filter(description__icontains='Nexen')
        count_desc = wrong_desc.count()
        wrong_desc.update(description="")
        self.stdout.write(self.style.SUCCESS(f"✅ Видалено {count_desc} помилкових описів."))

        # 2. ПРИМУСОВЕ СКАТУВАННЯ ФОТО (Для тих, у кого No Img у каталозі)
        # Беремо товари, де поле photo порожнє, але є посилання від Омеги
        products_no_file = Product.objects.filter(photo='').exclude(photo_url='')
        
        self.stdout.write(self.style.WARNING(f"📸 Спроба завантажити {products_no_file.count()} фото з Омеги..."))

        headers = {'User-Agent': 'Mozilla/5.0'}
        count_img = 0

        for product in products_no_file:
            try:
                res = requests.get(product.photo_url, headers=headers, timeout=10)
                if res.status_code == 200:
                    filename = f"tire_{product.id}.jpg"
                    product.photo.save(filename, ContentFile(res.content), save=True)
                    count_img += 1
                    if count_img % 50 == 0:
                        self.stdout.write(f"📥 Завантажено {count_img}...")
            except:
                continue

        self.stdout.write(self.style.SUCCESS(f"🎉 Готово! Оновлено описів: {count_desc}, додано фото: {count_img}"))
