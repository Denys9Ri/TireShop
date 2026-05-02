import requests
import time
import zipfile
import io
import pandas as pd
import re
from django.core.management.base import BaseCommand
from store.models import Product, Brand
from django.db import transaction

class Command(BaseCommand):
    help = 'Автоматичне оновлення залишків, цін та додавання нових товарів з API Омега'

    def handle(self, *args, **options):
        KEY = "ORMX5xgdRK5aqkFU8nlKfRv1rtnJmwc7"
        PRICE_ID = 39

        self.stdout.write(self.style.WARNING("1️⃣ Запуск синхронізації з Омега API..."))
        
        req = requests.post("https://public.omega.page/public/api/v1.0/price/enqueuePrice", json={"Key": KEY, "Id": PRICE_ID})
        if req.status_code != 200:
            self.stdout.write(self.style.ERROR(f"❌ Помилка API черги. Статус: {req.status_code}"))
            return

        self.stdout.write("⏳ Прайс замовлено. Очікуємо формування файлу на сервері Омеги...")

        download_url = "https://public.omega.page/public/api/v1.0/price/downloadPrice"
        file_content = None
        
        for i in range(20):
            time.sleep(15)
            res = requests.post(download_url, json={"Key": KEY, "Id": PRICE_ID})
            
            if res.status_code == 200:
                file_content = res.content
                self.stdout.write(self.style.SUCCESS("✅ ZIP-Архів успішно завантажено!"))
                break
            else:
                self.stdout.write(f"   ...ще формується (спроба {i+1}/20)")

        if not file_content:
            self.stdout.write(self.style.ERROR("❌ Сервер Омеги не віддав файл за 5 хвилин. Спробуйте пізніше."))
            return

        self.stdout.write(self.style.WARNING("2️⃣ Розпакування та аналіз прайсу..."))
        try:
            with zipfile.ZipFile(io.BytesIO(file_content)) as z:
                filename = z.namelist()[0]
                with z.open(filename) as f:
                    df = pd.read_excel(f, sheet_name='Шини Легкові', skiprows=7, engine='xlrd')
            
            df.columns = df.columns.str.replace(r'\s+', ' ', regex=True).str.strip()
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Помилка читання Excel: {e}"))
            return

        if 'Товар' not in df.columns:
            self.stdout.write(self.style.ERROR(f"❌ Не знайдено потрібних колонок у прайсі!"))
            return

        self.stdout.write(self.style.SUCCESS(f"📊 Знайдено {len(df)} рядків товарів. Починаємо оновлення бази..."))

        updated_count = 0
        created_count = 0
        error_count = 0

        # Обнуляємо всі залишки на сайті перед початком
        Product.objects.update(stock_quantity=0)

        with transaction.atomic():
            for index, row in df.iterrows():
                name_in_excel = str(row.get('Товар', '')).strip()
                
                if not name_in_excel or name_in_excel == 'nan':
                    continue

                # --- ПІДРАХУНОК ЗАЛИШКІВ (Київ + Львів) ---
                raw_kyiv = str(row.get('Вільний залишок Київ', '0')).replace('>', '').replace('<', '').strip()
                try:
                    stock_kyiv = int(float(raw_kyiv))
                except ValueError:
                    stock_kyiv = 0

                raw_lviv = str(row.get('Вільний залишок Львів', '0')).replace('>', '').replace('<', '').strip()
                try:
                    stock_lviv = int(float(raw_lviv))
                except ValueError:
                    stock_lviv = 0

                stock = stock_kyiv + stock_lviv
                if stock > 20:
                    stock = 20
                # ----------------------------------------

                # Ціни
                raw_price = str(row.get('Інтернет ціна', '0')).replace(' ', '').replace(',', '.').strip()
                try:
                    price = float(raw_price)
                except ValueError:
                    price = 0.0
                    
                # Отримуємо ціну закупки (опціонально, якщо вона потрібна в базі)
                raw_cost_price = str(row.get('Ваша ціна', '0')).replace(' ', '').replace(',', '.').strip()
                try:
                    cost_price = float(raw_cost_price)
                except ValueError:
                    cost_price = 0.0

                # Параметри для пошуку/створення
                brand_str = str(row.get('Виробник', '')).split(',')[0].strip()
                size_str = str(row.get('Типорозмір', '')).strip()
                diam_str = str(row.get('Діаметр', '')).strip()
                season_str = str(row.get('Сезонність', '')).strip()

                w_match = re.search(r'(\d{3})', size_str)
                p_match = re.search(r'/(\d{2,3})', size_str)
                d_match = re.search(r'(\d{2})', diam_str)

                w = int(w_match.group(1)) if w_match else None
                p = int(p_match.group(1)) if p_match else None
                d = int(d_match.group(1)) if d_match else None

                # 1. Прямий збіг по назві
                product = Product.objects.filter(name__iexact=name_in_excel).first()
                
                # 2. Розумний пошук
                if not product and w and p and d and brand_str:
                    candidates = Product.objects.filter(
                        width=w, profile=p, diameter=d, 
                        brand__name__icontains=brand_str
                    )

                    if candidates.count() == 1:
                        product = candidates.first()
                    elif candidates.count() > 1:
                        excel_words = re.findall(r'[a-z0-9а-яієї]+', name_in_excel.lower())
                        for c in candidates:
                            db_words = re.findall(r'[a-z0-9а-яієї]+', c.name.lower())
                            db_words = [word for word in db_words if word not in ['шина', 'під', 'шип']]
                            
                            if db_words and all(word in excel_words for word in db_words):
                                product = c
                                break

                # 3. ОНОВЛЕННЯ АБО СТВОРЕННЯ
                if product:
                    # Оновлюємо існуючий
                    product.stock_quantity = stock
                    if price > 0:
                        product.price = price
                    product.save()
                    updated_count += 1
                else:
                    # СТВОРЮЄМО НОВИЙ
                    if w and p and d and brand_str:
                        # Знаходимо або створюємо бренд
                        brand_obj, created = Brand.objects.get_or_create(name=brand_str)
                        
                        # Конвертуємо сезонність Омеги у формат нашої бази
                        seasonality = 'S' # Літо за замовчуванням
                        if 'Зима' in season_str:
                            seasonality = 'W'
                        elif 'сезон' in season_str.lower():
                            seasonality = 'A'
                        
                        try:
                            # Генеруємо чисту назву без слова "Шина"
                            clean_name = name_in_excel.replace('Шина ', '')
                            
                            new_product = Product.objects.create(
                                name=clean_name,
                                brand=brand_obj,
                                width=w,
                                profile=p,
                                diameter=d,
                                seasonality=seasonality,
                                price=price,
                                # Якщо у вас в моделі є cost_price, можна додати: cost_price=cost_price,
                                stock_quantity=stock,
                                # Опис порожній, бо Омега його не дає
                                description="", 
                            )
                            created_count += 1
                        except Exception as e:
                            # Якщо є якісь обмеження в базі (унікальність тощо)
                            error_count += 1
                    else:
                        # Якщо Омега не вказала розміри, ми не можемо створити шину
                        error_count += 1

        self.stdout.write(self.style.SUCCESS(f"\n🎉 ГОТОВО!"))
        self.stdout.write(self.style.SUCCESS(f"🔄 Оновлено існуючих товарів: {updated_count}"))
        self.stdout.write(self.style.WARNING(f"➕ Створено нових товарів: {created_count}"))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"⚠️ Пропущено (некоректні дані): {error_count}"))
