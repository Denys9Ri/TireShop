import requests
from django.core.management.base import BaseCommand
from store.models import Product
from django.core.files.base import ContentFile

class Command(BaseCommand):
    help = 'Примусове оновлення фото з Омеги (ігноруючи старі записи)'

    def handle(self, *args, **options):
        # Беремо товари, де є URL від Омеги
        products = Product.objects.filter(photo_url__isnull=False).exclude(photo_url='')
        
        self.stdout.write(self.style.WARNING(f"🚀 Починаємо повне перезавантаження для {products.count()} товарів..."))

        count = 0
        for product in products:
            try:
                # Ми НЕ перевіряємо product.photo, а просто качаємо за посиланням
                self.stdout.write(f"📥 Завантаження для: {product.name}")
                
                res = requests.get(product.photo_url, timeout=10)
                if res.status_code == 200:
                    filename = f"tire_{product.id}.jpg"
                    # save=True оновить поле в базі і запише файл на диск
                    product.photo.save(filename, ContentFile(res.content), save=True)
                    count += 1
                    self.stdout.write(self.style.SUCCESS(f"✅ Готово #{count}"))
                else:
                    self.stdout.write(self.style.ERROR(f"⚠️ Помилка сервера: {res.status_code}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Помилка: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\n🎉 ПЕРЕМОГА! Оновлено фото для {count} товарів."))
