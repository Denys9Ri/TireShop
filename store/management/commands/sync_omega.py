import requests
import time
import zipfile
import io
import pandas as pd
import re
from django.core.management.base import BaseCommand
from store.models import Product, Brand
from django.db import reset_queries # Додали для очищення пам'яті

def clean_price_value(val):
    try:
        if pd.isna(val): return 0.0
        if isinstance(val, (int, float)): return float(val)
        
        s = str(val).strip().replace(',', '.')
        s = re.sub(r'[^\d\.]', '', s)
        
        if not s: return 0.0
        
        parts = s.split('.')
        if len(parts) > 2: 
            s = ''.join(parts[:-1]) + '.' + parts[-1]
            
        return float(s)
    except Exception:
        return 0.0

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

        self.stdout.write("⏳ Прайс замовлено. Очікуємо формування файлу...")

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
            self.stdout.write(self.style.ERROR("❌ Сервер Омеги не віддав файл."))
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

        updated_count = 0
        created_count = 0
        error_count = 0
        zero_price_count = 0

        Product.objects.update(stock_quantity=0)

        self.stdout.write(self.style.WARNING("🔄 Починаємо запис у базу... (це може зайняти пару хвилин)"))

        for index, row in df.iterrows():
            name_in_excel = str(row.get('Товар', '')).strip()
            if not name_in_excel or name_in_excel == 'nan':
                continue

            stock_kyiv = clean_price_value(row.get('Вільний залишок Київ', 0))
            stock_lviv = clean_price_value(row.get('Вільний залишок Львів', 0))
            stock = int(stock_kyiv + stock_lviv)
            if stock > 20: stock = 20

            price_internet = clean_price_value(row.get('Інтернет ціна'))
            price_retail = clean_price_value(row.get('Роздрібна ціна'))
            price_cost = clean_price_value(row.get('Ваша ціна'))

            final_price = price_internet
            if final_price <= 0: final_price = price_retail
            if final_price <= 0: final_price = price_cost

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

            product = None
            clean_name_excel = name_in_excel.replace('Шина ', '').strip()
            product = Product.objects.filter(name__iexact=clean_name_excel).first()
            if not product:
                product = Product.objects.filter(name__iexact=name_in_excel).first()

            if not product and w and p and d and brand_str:
                candidates = Product.objects.filter(width=w, profile=p, diameter=d, brand__name__icontains=brand_str)
                if candidates.count() == 1:
                    product = candidates.first()
                elif candidates.count() > 1:
                    for c in candidates:
                        model_parts = re.findall(r'[a-zA-Z0-9]+', c.name)
                        if any(m.lower() in name_in_excel.lower() for m in model_parts if len(m) > 2):
                            product = c
                            break

            if product:
                product.stock_quantity = stock
                if final_price > 0:
                    product.price = final_price
                else:
                    zero_price_count += 1
                
                product.save()
                updated_count += 1

                # Виводимо прогрес кожні 100 товарів і чистимо пам'ять!
                if updated_count % 100 == 0:
                    self.stdout.write(f"   ...вже оновлено {updated_count} товарів...")
                    reset_queries() # Рятує від зависання терміналу (очищає оперативну пам'ять)

            else:
                if w and p and d and brand_str:
                    brand_obj, created = Brand.objects.get_or_create(name=brand_str)
                    seasonality = 'S'
                    if 'Зима' in season_str: seasonality = 'W'
                    elif 'сезон' in season_str.lower(): seasonality = 'A'
                    
                    try:
                        clean_name = name_in_excel.replace('Шина ', '')
                        new_product = Product.objects.create(
                            name=clean_name, brand=brand_obj,
                            width=w, profile=p, diameter=d, seasonality=seasonality,
                            price=final_price, stock_quantity=stock, description="", 
                        )
                        if final_price <= 0: zero_price_count += 1
                        created_count += 1
                    except Exception:
                        error_count += 1
                else:
                    error_count += 1

        self.stdout.write(self.style.SUCCESS(f"\n🎉 ГОТОВО!"))
        self.stdout.write(self.style.SUCCESS(f"🔄 Оновлено існуючих товарів: {updated_count}"))
        if created_count > 0:
            self.stdout.write(self.style.WARNING(f"➕ Створено нових товарів: {created_count}"))
        if zero_price_count > 0:
            self.stdout.write(self.style.ERROR(f"⚠️ Товарів без ціни (залишено 0): {zero_price_count}"))
