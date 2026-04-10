import requests
import time
from django.core.management.base import BaseCommand
from store.models import Product
from django.core.files.base import ContentFile
from django.db.models import Q  # <--- Додали магічний інструмент для пошуку

class Command(BaseCommand):
    help = 'Пошук чистих фото в мережі через Serper.dev'

    def handle(self, *args, **options):
        self.stdout.write("🤖 Запуск партизанського бота для пошуку фотографій...")
        
        # Твій робочий ключ від Serper
        API_KEY = "44e0f1314e3d0244bc5e38b63cecfb6d38c02032"

        # Тепер ми шукаємо і NULL, і порожні рядки ("")
        products = Product.objects.filter(Q(photo__isnull=True) | Q(photo__exact=''))
        
        if not products:
            self.stdout.write("✅ Всі товари дійсно вже мають фотографії!")
            return

        # Чорний список (сайти з водяними знаками)
        black_list = ['omega.page', 'infoshina', 'shina.ua', 'rozetka', 'prom.ua', 'autoshina']

        for product in products:
            # Формуємо хитрий запит, використовуючи твої реальні поля
            brand_name = product.brand.name if product.brand else ""
            
            search_query = f"{brand_name} {product.name} {product.width}/{product.profile} R{product.diameter} tire"
            
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
                            # Зберігаємо картинку в поле photo!
                            file_name = f"tire_{product.id}_{product.slug[:20]}.jpg"
                            product.photo.save(file_name, ContentFile(img_response.content))
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
