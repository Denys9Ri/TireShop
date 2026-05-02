import requests
import time
import zipfile
import io
import pandas as pd
import re
from django.core.management.base import BaseCommand
from store.models import Product
from django.db import transaction

class Command(BaseCommand):
    help = 'Автоматичне оновлення залишків та цін з API Омега'

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

        if 'Товар' not in df.columns or 'Загальний залишок' not in df.columns:
            self.stdout.write(self.style.ERROR(f"❌ Не знайдено потрібних колонок у прайсі!"))
            return

        self.stdout.write(self.style.SUCCESS(f"📊 Знайдено {len(df)} рядків товарів. Починаємо оновлення бази..."))

        updated_count = 0
        not_found_count = 0
        not_found_examples = []

        Product.objects.update(stock_quantity=0)

        with transaction.atomic():
            for index, row in df.iterrows():
                name_in_excel = str(row.get('Товар', '')).strip()
                
                if not name_in_excel or name_in_excel == 'nan':
                    continue

                raw_stock = str(row.get('Загальний залишок', '0')).replace('>', '').replace('<', '').strip()
                try:
                    stock = int(float(raw_stock))
                except ValueError:
                    stock = 0

                raw_price = str(row.get('Інтернет ціна', '0')).replace(' ', '').replace(',', '.').strip()
                try:
                    price = float(raw_price)
                except ValueError:
                    price = 0.0

                # 1. СПРОБА: Прямий збіг по назві
                product = Product.objects.filter(name__iexact=name_in_excel).first()
                
                # 2. РОЗУМНА СПРОБА: Шукаємо за параметрами (бренд, ширина, профіль, радіус)
                if not product:
                    brand_str = str(row.get('Виробник', '')).strip()
                    size_str = str(row.get('Типорозмір', '')).strip()
                    diam_str = str(row.get('Діаметр', '')).strip()

                    # Витягуємо цифри з колонок "155/65R13" та "13"
                    w_match = re.search(r'(\d{3})', size_str)
                    p_match = re.search(r'/(\d{2,3})', size_str)
                    d_match = re.search(r'(\d{2})', diam_str)

                    if w_match and p_match and d_match and brand_str:
                        w = int(w_match.group(1))
                        p = int(p_match.group(1))
                        d = int(d_match.group(1))

                        # Шукаємо всі товари цього розміру і бренду
                        candidates = Product.objects.filter(
                            width=w, profile=p, diameter=d, 
                            brand__name__icontains=brand_str
                        )

                        if candidates.count() == 1:
                            # Знайшли тільки одну таку шину — це вона!
                            product = candidates.first()
                        elif candidates.count() > 1:
                            # Якщо є кілька моделей, перевіряємо, чи слова з нашої назви є в назві Омеги
                            for c in candidates:
                                model_words = c.name.lower().replace('шина', '').split()
                                if model_words and all(word in name_in_excel.lower() for word in model_words):
                                    product = c
                                    break

                # Якщо товар остаточно знайдено — оновлюємо
                if product:
                    product.stock_quantity = stock
                    if price > 0:
                        product.price = price
                    product.save()
                    updated_count += 1
                else:
                    not_found_count += 1
                    if len(not_found_examples) < 15:
                        not_found_examples.append(name_in_excel)

        self.stdout.write(self.style.SUCCESS(f"\n🎉 ГОТОВО! Оновлено товарів: {updated_count}"))
        if not_found_count > 0:
            self.stdout.write(self.style.WARNING(f"⚠️ Не знайдено збігів: {not_found_count}"))
            self.stdout.write("\n📝 ПРИКЛАДИ НАЗВ З ПРАЙСУ, ЯКІ НЕ ЗНАЙШЛИСЯ:")
            for ex in not_found_examples:
                self.stdout.write(f" - {ex}")
