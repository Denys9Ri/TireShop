import requests
import time
from django.core.management.base import BaseCommand
from store.models import Product
from django.core.files.base import ContentFile

class Command(BaseCommand):
    help = 'Пошук чистих фото в мережі через Serper.dev'

    def handle(self, *args, **options):
        self.stdout.write("🤖 Запуск партизанського бота для пошуку фотографій...")
        
        # 🔥 ВСТАВ СВІЙ СКОПІЙОВАНИЙ КЛЮЧ ВІД SERPER ТУТ:
        API_KEY = "9ac8ffb82d47caf4dd46e223217e9f3361222a54"
        
        if API_KEY == "9ac8ffb82d47caf4dd46e223217e9f3361222a54":
            self.stderr.write("❌ Стоп! Ви забули вставити API ключ.")
            return

        # Шукаємо товари, у яких немає фото. 
        # УВАГА: якщо твоє поле з фотографією в моделі називається 'photo', 
        # заміни 'image__isnull' на 'photo__isnull' нижче!
        products = Product.objects.filter(image__isnull=True, is_active=True)[:5] 
        
        if not products:
            self.stdout.write("✅ Всі товари вже мають фотографії!")
            return

        # Чорний список (сайти з водяними знаками)
        black_list = ['omega.page', 'infoshina', 'shina.ua', 'rozetka', 'prom.ua', 'autoshina']

        for product in products:
            # Формуємо хитрий запит (додаємо слово "tire" або "шина" для точності)
            search_query = f"{product.brand.name if product.brand else ''} {product.model} {product.size} tire"
            self.stdout.write(f"\n🔎 Шукаємо: {search_query}")
            
            search_url = "https://google.serper.dev/images"
            headers = {
                'X-API-KEY': API_KEY,
                'Content-Type': 'application/json'
            }
            data = {"q": search_query, "num": 10} # Просимо 10 картинок на вибір
            
            try:
                response = requests.post(search_url, json=data, headers=headers)
                results = response.json().get('images', [])
                
                image_saved = False
                
                for img in results:
                    img_url = img.get('imageUrl')
                    source = img.get('source').lower()
                    
                    # Перевіряємо, чи немає цього сайту в чорному списку
                    if any(bad_site in source for bad_site in black_list):
                        self.stdout.write(f"   ⚠️ Пропускаємо {source} (чорний список)")
                        continue
                        
                    self.stdout.write(f"   📥 Спроба завантажити з {source}...")
                    
                    try:
                        # Качаємо картинку (даємо їй 5 секунд на роздуми)
                        img_response = requests.get(img_url, timeout=5)
                        
                        if img_response.status_code == 200:
                            # Зберігаємо картинку!
                            # Якщо поле називається 'photo', заміни product.image на product.photo
                            file_name = f"tire_{product.id}_{product.slug[:20]}.jpg"
                            product.image.save(file_name, ContentFile(img_response.content))
                            self.stdout.write(f"   ✅ УСПІХ! Фото збережено.")
                            image_saved = True
                            break # Фото знайшли, йдемо до наступного товару
                    except Exception as e:
                        self.stdout.write(f"   ❌ Помилка скачування: {e}")
                        continue
                
                if not image_saved:
                    self.stdout.write("   😔 Не вдалося знайти чисте фото для цього товару.")
                    
            except Exception as e:
                self.stderr.write(f"❌ Помилка пошуку в Serper: {e}")
            
            # Робимо паузу 2 секунди, щоб Гугл не запідозрив, що ми бот
            time.sleep(2)
            
        self.stdout.write("\n🏁 Пошуковий рейд завершено!")
