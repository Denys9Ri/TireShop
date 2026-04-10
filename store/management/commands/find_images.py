import requests
import time
from django.core.management.base import BaseCommand
from store.models import Product
from django.core.files.base import ContentFile
from django.db.models import Q

class Command(BaseCommand):
    help = 'Пошук чистих фото в мережі через Serper.dev'

    def handle(self, *args, **options):
        self.stdout.write("🤖 Запуск партизанського бота для пошуку фотографій...")
        
        # 🔥 ВСТАВ СВІЙ НОВИЙ КЛЮЧ ВІД SERPER ТУТ 🔥
        API_KEY = "63360c318daf0d05c5148894689ceab40bf1e5f4"

        # --- БЛОК ОЧИЩЕННЯ ФАНТОМІВ ---
        self.stdout.write("🧹 Перевірка бази на наявність 'фантомних' фотографій...")
        ghosts = Product.objects.exclude(Q(photo__isnull=True) | Q(photo__exact=''))
        ghost_count = 0
        for p in ghosts:
            if p.photo and not p.photo.storage.exists(p.photo.name):
                p.photo = None
                p.save()
                ghost_count += 1
                
        if ghost_count > 0:
            self.stdout.write(f"✅ Видалено {ghost_count} фантомних записів (файли яких були приховані сховищем).")
        else:
            self.stdout.write("✅ Фантомів не знайдено.")
        # ------------------------------

        # Шукаємо товари без фото
        products = Product.objects.filter(Q(photo__isnull=True) | Q(photo__exact=''))
        
        if not products:
            self.stdout.write("✅ Всі товари дійсно вже мають фотографії!")
            return

        # Чорний список
        black_list = ['omega.page', 'infoshina', 'shina.ua', 'rozetka', 'prom.ua', 'autoshina']

        for product in products:
            brand_name = product.brand.name if product.brand else ""
            search_query = f"{brand_name} {product.name} {product.width}/{product.profile} R{product.diameter} tire"
            
            self.stdout.write(f"\n🔎 Шукаємо: {search_query}")
            
            search_url = "https://google.serper.dev/images"
            headers = {
                'X-API-KEY': API_KEY,
                'Content-Type': 'application/json'
            }
            data = {"q": search_query, "num": 10}
            
            try:
                response = requests.post(search_url, json=data, headers=headers)
                
                if response.status_code == 403:
                    self.stderr.write("❌ ПОМИЛКА 403: Ліміт запитів вичерпано або ключ недійсний!")
                    return
                    
                results = response.json().get('images', [])
                image_saved = False
                
                for img in results:
                    img_url = img.get('imageUrl')
                    source = img.get('source').lower()
                    
                    if any(bad_site in source for bad_site in black_list):
                        self.stdout.write(f"   ⚠️ Пропускаємо {source} (чорний список)")
                        continue
                        
                    self.stdout.write(f"   📥 Спроба завантажити з {source}...")
                    
                    try:
                        img_response = requests.get(img_url, timeout=5)
                        if img_response.status_code == 200:
                            file_name = f"tire_{product.id}_{product.slug[:20]}.jpg"
                            product.photo.save(file_name, ContentFile(img_response.content))
                            self.stdout.write(f"   ✅ УСПІХ! Фото збережено.")
                            image_saved = True
                            break
                    except Exception as e:
                        self.stdout.write(f"   ❌ Помилка скачування: {e}")
                        continue
                
                if not image_saved:
                    self.stdout.write("   😔 Не вдалося знайти чисте фото для цього товару.")
                    
            except Exception as e:
                self.stderr.write(f"❌ Помилка пошуку в Serper: {e}")
            
            time.sleep(2)
            
        self.stdout.write("\n🏁 Пошуковий рейд завершено!")
