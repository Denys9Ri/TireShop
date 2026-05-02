import os
import requests
import time
import re
from django.core.management.base import BaseCommand
from store.models import Product
from django.core.files.base import ContentFile

class Command(BaseCommand):
    help = 'Смарт-пошук якісних фото через Google (Serper) з обходом помилок'

    def clean_name(self, name):
        """Очищає назву шини для кращого пошуку в Google"""
        # Видаляємо слово "Шина" та зайві пробіли
        name = name.replace('Шина', '').strip()
        # Видаляємо все в дужках (країни виробники, замітки)
        name = re.sub(r'\(.*?\)', '', name)
        # Видаляємо спецсимволи, що збивають пошук
        name = name.replace('*', ' ').replace('"', '').replace('?', '').strip()
        # Прибираємо подвійні пробіли
        name = ' '.join(name.split())
        return name

    def handle(self, *args, **options):
        # Працюємо тільки з товарами без фото
        products = Product.objects.filter(photo='').exclude(name='')
        
        self.stdout.write(self.style.WARNING(f"🚀 Починаємо смарт-обробку {products.count()} товарів..."))
        
        # Отримуємо ключ з системи або впиши його сюди прямо
        serper_key = os.environ.get("SERPER_API_KEY", "ВАШ_КЛЮЧ_ТУТ")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        }

        count = 0
        for product in products:
            search_query = self.clean_name(product.name)
            success = False
            
            try:
                # 1. Запит до Serper API
                url = "https://google.serper.dev/images"
                payload = {"q": f"шина {search_query} фото", "num": 1}
                s_headers = {
                    'X-API-KEY': serper_key,
                    'Content-Type': 'application/json'
                }
                
                response = requests.post(url, json=payload, headers=s_headers, timeout=15)
                
                if response.status_code == 200:
                    results = response.json().get('images', [])
                    
                    if results:
                        img_url = results[0]['imageUrl']
                        
                        # 2. Спроба завантажити саме зображення
                        try:
                            img_res = requests.get(img_url, headers=headers, timeout=15)
                            if img_res.status_code == 200:
                                # Зберігаємо файл
                                ext = img_url.split('.')[-1].split('?')[0][:3]
                                if ext not in ['jpg', 'png', 'web']: ext = 'jpg'
                                
                                product.photo.save(f"tire_{product.id}.{ext}", ContentFile(img_res.content), save=True)
                                self.stdout.write(self.style.SUCCESS(f"🔍 [Google] {search_query}"))
                                success = True
                                count += 1
                                # Пауза, щоб не заблокували за швидкість
                                time.sleep(1) 
                            else:
                                self.stdout.write(self.style.WARNING(f"⚠️ Джерело відхилило запит (403): {search_query}"))
                        except Exception:
                            self.stdout.write(self.style.ERROR(f"❌ Помилка завантаження файлу для {search_query}"))
                    else:
                        self.stdout.write(self.style.ERROR(f"🤷 Google не знайшов фото: {search_query}"))
                else:
                    self.stdout.write(self.style.ERROR(f"📡 Помилка Serper API (Статус: {response.status_code})"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"💥 Критична помилка для {search_query}"))

        self.stdout.write(self.style.SUCCESS(f"\n🎉 Роботу завершено! Додано {count} нових фото."))
