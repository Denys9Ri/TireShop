import requests
import time
import re
import os
from django.core.management.base import BaseCommand
from store.models import Product
from django.core.files.base import ContentFile
from django.db.models import Q

def get_clean_model_name(name_str):
    s = str(name_str)
    s = re.sub(r'\d{3}/\d{2,3}\s?[RZRzr]?\d{2}', '', s)
    s = re.sub(r'\b\d{2,3}[a-zA-Z]\b', '', s)
    s = re.sub(r'\b(XL|RunFlat|RFT|EXTRA LOAD)\b', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\(.*?\)', '', s)
    s = s.replace('Шина', '').replace('під шип', '')
    s = re.sub(r'[^\w\s-]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

class Command(BaseCommand):
    help = 'Пошук чистих фото в мережі через Serper.dev'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("🤖 Запуск партизанського бота для пошуку фотографій..."))
        
        # Беремо ключ з Coolify, але якщо його там немає (наприклад, запускаємо локально) - використовуємо напряму
        API_KEY = os.environ.get("SERPER_API_KEY", "63360c318daf0d05c5148894689ceab40bf1e5f4")

        # Очищення фантомів
        self.stdout.write("🧹 Перевірка бази на наявність 'фантомних' фотографій...")
        ghosts = Product.objects.exclude(Q(photo__isnull=True) | Q(photo__exact=''))
        ghost_count = 0
        for p in ghosts:
            if p.photo and not p.photo.storage.exists(p.photo.name):
                p.photo = None
                p.save()
                ghost_count += 1
                
        if ghost_count > 0:
            self.stdout.write(self.style.SUCCESS(f"✅ Видалено {ghost_count} фантомних записів."))
        else:
            self.stdout.write(self.style.SUCCESS("✅ Фантомів не знайдено."))

        # Шукаємо товари без фото
        products = Product.objects.filter(Q(photo__isnull=True) | Q(photo__exact=''))
        
        if not products:
            self.stdout.write(self.style.SUCCESS("✅ Всі товари дійсно вже мають фотографії!"))
            return

        black_list = ['omega.page', 'infoshina', 'shina.ua', 'rozetka', 'prom.ua', 'autoshina']

        for product in products:
            brand_name = product.brand.name if product.brand else ""
            clean_model = get_clean_model_name(product.name)
            
            search_query = f"{brand_name} {clean_model} tire"
            self.stdout.write(f"\n🔎 Шукаємо: '{search_query}'")
            
            search_url = "https://google.serper.dev/images"
            headers = {
                'X-API-KEY': API_KEY,
                'Content-Type': 'application/json'
            }
            data = {"q": search_query, "num": 10}
            
            try:
                response = requests.post(search_url, json=data, headers=headers)
                
                # 🔥 РЕНТГЕН ПОМИЛОК 🔥
                if response.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"   ❌ Сервер Serper відмовив! Код: {response.status_code}. Відповідь: {response.text}"))
                    return # Зупиняємо скрипт, щоб не спамити помилками
                    
                results = response.json().get('images', [])
                
                if not results:
                    self.stdout.write(self.style.WARNING(f"   ⚠️ Serper повернув 0 картинок. Відповідь: {response.text}"))
                    continue

                image_saved = False
                
                for img in results:
                    img_url = img.get('imageUrl')
                    source = img.get('source').lower() if img.get('source') else ""
                    
                    if any(bad_site in source for bad_site in black_list):
                        self.stdout.write(f"   ⚠️ Пропускаємо {source} (чорний список)")
                        continue
                        
                    self.stdout.write(f"   📥 Завантаження з {source}...")
                    
                    try:
                        img_response = requests.get(img_url, timeout=5)
                        if img_response.status_code == 200:
                            file_name = f"tire_{product.id}_{product.slug[:20]}.jpg"
                            product.photo.save(file_name, ContentFile(img_response.content))
                            self.stdout.write(self.style.SUCCESS(f"   ✅ УСПІХ! Фото збережено."))
                            image_saved = True
                            break
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"   ❌ Помилка скачування: {e}"))
                        continue
                
                if not image_saved:
                    self.stdout.write("   😔 Не вдалося знайти чисте фото для цього товару.")
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Помилка пошуку: {e}"))
            
            time.sleep(1)
            
        self.stdout.write(self.style.SUCCESS("\n🏁 Пошуковий рейд завершено!"))
