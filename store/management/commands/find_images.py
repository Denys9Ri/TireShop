import os
import requests
import time
import re
from django.core.management.base import BaseCommand
from store.models import Product
from django.core.files.base import ContentFile

class Command(BaseCommand):
    help = 'Смарт-пошук фото через Google (Serper) з очищенням назв'

    def clean_name(self, name):
        # Видаляємо слово "Шина", дужки та країну виробника
        name = name.replace('Шина', '').strip()
        name = re.sub(r'\(.*?\)', '', name)
        # Видаляємо зайві символи, що заважають пошуку
        name = name.replace('*', ' ').replace('"', '').strip()
        return name

    def handle(self, *args, **options):
        # Працюємо ТІЛЬКИ з тими, де взагалі немає фото
        products = Product.objects.filter(photo='').exclude(name='')
        
        self.stdout.write(self.style.WARNING(f"🚀 Починаємо смарт-обробку {products.count()} товарів..."))
        
        serper_key = os.environ.get("SERPER_API_KEY", "ВАШ_КЛЮЧ_ТУТ")
        headers = {'User-Agent': 'Mozilla/5.0'}

        count = 0
        for product in products:
            # Чистимо назву для Google
            search_query = self.clean_name(product.name)
            
            try:
                url = "https://google.serper.dev/images"
                payload = {"q": f"шина {search_query} фото", "num": 1}
                s_headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
                
                response = requests.post(url, json=payload, headers=s_headers)
                results = response.json().get('images', [])
                
                if results:
                    img_url = results[0]['imageUrl']
                    img_res = requests.get(img_url, headers=headers, timeout=10)
                    if img_res.status_code == 200:
                        product.photo.save(f"tire_{product.id}.jpg", ContentFile(img_res.content), save=True)
                        self.stdout.write(self.style.SUCCESS(f"🔍 [Google] {search_query}"))
                        count += 1
                        time.sleep(0.7) # Трохи більша пауза для стабільності
                else:
                    self.stdout.write(self.style.ERROR(f"🤷 Не знайдено: {search_query}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Помилка для {search_query}"))

        self.stdout.write(self.style.SUCCESS(f"🎉 Готово! Додано {count} нових фото."))
