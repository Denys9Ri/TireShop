import os
import requests
import time
from django.core.management.base import BaseCommand
from store.models import Product
from django.core.files.base import ContentFile

class Command(BaseCommand):
    help = 'Смарт-пошук фото: Омега (з обходом 403) + Serper'

    def handle(self, *args, **options):
        # Шукаємо тільки ті товари, де фото поле порожнє
        products = Product.objects.filter(photo='').exclude(name='')
        
        self.stdout.write(self.style.WARNING(f"🚀 Починаємо фінальну обробку {products.count()} товарів..."))
        
        # Заголовки, щоб сервери не бачили в нас бота
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
        }
        
        serper_key = os.environ.get("SERPER_API_KEY", "ВАШ_КЛЮЧ_ТУТ_ЯКЩО_НЕМАЄ_В_ENV")

        count = 0
        for product in products:
            success = False
            
            # 1. Пробуємо завантажити за посиланням Омеги з новими заголовками
            if product.photo_url:
                try:
                    res = requests.get(product.photo_url, headers=headers, timeout=10)
                    if res.status_code == 200:
                        product.photo.save(f"tire_{product.id}.jpg", ContentFile(res.content), save=True)
                        self.stdout.write(self.style.SUCCESS(f"✅ [Омега-Fix] {product.name}"))
                        success = True
                except:
                    pass

            # 2. Якщо не вийшло - йдемо в Serper (Google)
            if not success and serper_key:
                try:
                    url = "https://google.serper.dev/images"
                    payload = {"q": f"шина {product.name} фото", "num": 1}
                    s_headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
                    
                    response = requests.post(url, json=payload, headers=s_headers)
                    results = response.json().get('images', [])
                    
                    if results:
                        img_url = results[0]['imageUrl']
                        img_res = requests.get(img_url, headers=headers, timeout=10)
                        if img_res.status_code == 200:
                            product.photo.save(f"tire_{product.id}.jpg", ContentFile(img_res.content), save=True)
                            self.stdout.write(self.style.SUCCESS(f"🔍 [Google] {product.name}"))
                            success = True
                            time.sleep(0.5) # Мінімальна пауза
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Помилка Google для {product.name}"))

            if success:
                count += 1
                if count % 50 == 0:
                    self.stdout.write(self.style.WARNING(f"📈 Опрацьовано {count} товарів..."))

        self.stdout.write(self.style.SUCCESS(f"\n🎉 ФІНІШ! Додано {count} фото. Сайт повністю укомплектований!"))
