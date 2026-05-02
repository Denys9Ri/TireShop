import requests
import time
import re
import os
from django.core.management.base import BaseCommand
from store.models import Product
from django.core.files.base import ContentFile
from django.db.models import Q

# Функція, яка "відрізає" всі розміри і залишає тільки чисту модель (напр. "ALENZA 001")
def get_clean_model_name(name_str):
    s = str(name_str)
    # Видаляємо розміри типу 285/45R20 або 285/45 R20
    s = re.sub(r'\d{3}/\d{2,3}\s?[RZRzr]?\d{2}', '', s)
    # Видаляємо індекси швидкості/навантаження (напр. 108W, 99Y)
    s = re.sub(r'\b\d{2,3}[a-zA-Z]\b', '', s)
    # Видаляємо спец. позначення
    s = re.sub(r'\b(XL|RunFlat|RFT|EXTRA LOAD)\b', '', s, flags=re.IGNORECASE)
    # Видаляємо текст у дужках (напр. "(Bridgestone)")
    s = re.sub(r'\(.*?\)', '', s)
    # Видаляємо зайві слова
    s = s.replace('Шина', '').replace('під шип', '')
    # Прибираємо зайві пробіли та символи
    s = re.sub(r'[^\w\s-]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

class Command(BaseCommand):
    help = 'Пошук чистих фото в мережі через Serper.dev'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("🤖 Запуск партизанського бота для пошуку фотографій..."))
        
        # 🔥 Беремо ключ з налаштувань Coolify (БЕЗПЕЧНО!) 🔥
        API_KEY = os.environ.get("SERPER_API_KEY")
        
        if not API_KEY:
            self.stdout.write(self.style.ERROR("❌ Не знайдено SERPER_API_KEY у змінних оточеннях Coolify!"))
            return

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
            self.stdout.write(self.style.SUCCESS(f"✅ Видалено {ghost_count} фантомних записів."))
        else:
            self.stdout.write(self.style.SUCCESS("✅ Фантомів не знайдено."))
        # ------------------------------

        # Шукаємо товари без фото
        products = Product.objects.filter(Q(photo__isnull=True) | Q(photo__exact=''))
        
        if not products:
            self.stdout.write(self.style.SUCCESS("✅ Всі товари дійсно вже мають фотографії!"))
            return

        # Чорний список (сайти з водяними знаками або поганою якістю)
        black_list = ['omega.page', 'infoshina', 'shina.ua', 'rozetka', 'prom.ua', 'autoshina']

        for product in products:
            brand_name = product.brand.name if product.brand else ""
            clean_model = get_clean_model_name(product.name)
            
            # 🔥 Ідеальний запит для студійного фото шини 🔥
            search_query = f"{brand_name} {clean_model} tire"
            
            self.stdout.write(f"\n🔎 Шукаємо: '{search_query}' (Оригінал бази: {product.name[:30]}...)")
            
            search_url = "https://google.serper.dev/images"
            headers = {
                'X-API-KEY': API_KEY,
                'Content-Type': 'application/json'
            }
            data = {"q": search_query, "num": 10}
            
            try:
                response = requests.post(search_url, json=data, headers=headers)
                
                if response.status_code == 403:
                    self.stdout.write(self.style.ERROR("❌ ПОМИЛКА 403: Ліміт запитів вичерпано або ключ недійсний!"))
                    return
                    
                results = response.json().get('images', [])
                image_saved = False
                
                for img in results:
                    img_url = img.get('imageUrl')
                    source = img.get('source').lower() if img.get('source') else ""
                    
                    if any(bad_site in source for bad_site in black_list):
                        self.stdout.write(f"   ⚠️ Пропускаємо {source} (чорний список)")
                        continue
                        
                    self.stdout.write(f"   📥 Спроба завантажити з {source}...")
                    
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
                    self.stdout.write(self.style.WARNING("   😔 Не вдалося знайти чисте фото для цього товару."))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Помилка пошуку в Serper: {e}"))
            
            # Пауза, щоб не заблокували за спам
            time.sleep(1)
            
        self.stdout.write(self.style.SUCCESS("\n🏁 Пошуковий рейд завершено!"))
