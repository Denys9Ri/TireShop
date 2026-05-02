import os
import requests
import time
import re
from django.core.management.base import BaseCommand
from store.models import Product
from django.core.files.base import ContentFile

class Command(BaseCommand):
    help = 'Тільки якісні фото з Google. Жодної Омеги.'

    def clean_name(self, name):
        """Максимальне спрощення назви для успішного пошуку"""
        name = name.replace('Шина', '').strip()
        # Видаляємо все в дужках та зайві приписки
        name = re.sub(r'\(.*?\)', '', name)
        name = re.sub(r'DOT\d*', '', name) # Видаляємо рік випуску (DOT)
        name = name.replace('*', ' ').replace('"', '').replace('XL', '').strip()
        return ' '.join(name.split())

    def handle(self, *args, **options):
        # Шукаємо ТІЛЬКИ ті товари, де в полі photo (файл) нічого немає
        # На photo_url ми більше не дивимось взагалі
        products = Product.objects.filter(photo='').exclude(name='')
        
        self.stdout.write(self.style.WARNING(f"🚀 Шукаємо якісні фото для {products.count()} товарів..."))
        
        serper_key = os.environ.get("SERPER_API_KEY", "ВАШ_КЛЮЧ")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

        count = 0
        for product in products:
            search_query = self.clean_name(product.name)
            
            try:
                # Тільки Google через Serper
                url = "https://google.serper.dev/images"
                payload = {"q": f"tire {search_query} white background", "num": 1}
                # Додаємо "white background" для вищої якості та чистоти фото
                
                s_headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
                response = requests.post(url, json=payload, headers=s_headers, timeout=15)
                
                if response.status_code == 200:
                    results = response.json().get('images', [])
                    if results:
                        img_url = results[0]['imageUrl']
                        img_res = requests.get(img_url, headers=headers, timeout=15)
                        
                        if img_res.status_code == 200:
                            # Зберігаємо тільки файл
                            ext = img_url.split('.')[-1].split('?')[0][:3]
                            if ext not in ['jpg', 'png']: ext = 'jpg'
                            
                            product.photo.save(f"g_{product.id}.{ext}", ContentFile(img_res.content), save=True)
                            self.stdout.write(self.style.SUCCESS(f"✅ Google OK: {search_query}"))
                            count += 1
                            time.sleep(1) # Пауза для стабільності
                    else:
                        self.stdout.write(self.style.ERROR(f"🤷 Не знайдено в Google: {search_query}"))
            except Exception:
                continue

        self.stdout.write(self.style.SUCCESS(f"🎉 Завершено! Додано якісних фото: {count}"))
