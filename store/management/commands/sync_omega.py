import requests
import time
import zipfile
import io
import pandas as pd
from django.core.management.base import BaseCommand
from store.models import Product
from django.db import transaction

class Command(BaseCommand):
    help = 'Автоматичне оновлення залишків та цін з API Омега'

    def handle(self, *args, **options):
        KEY = "ORMX5xgdRK5aqkFU8nlKfRv1rtnJmwc7"
        PRICE_ID = 39

        self.stdout.write(self.style.WARNING("1️⃣ Запуск синхронізації з Омега API..."))
        
        # 1. Ставимо прайс в чергу
        req = requests.post("https://public.omega.page/public/api/v1.0/price/enqueuePrice", json={"Key": KEY, "Id": PRICE_ID})
        if req.status_code != 200:
            self.stdout.write(self.style.ERROR(f"❌ Помилка API черги. Статус: {req.status_code}"))
            return

        self.stdout.write("⏳ Прайс замовлено. Очікуємо формування файлу на сервері Омеги...")

        # 2. Чекаємо і скачуємо
        download_url = "https://public.omega.page/public/api/v1.0/price/downloadPrice"
        file_content = None
        
        for i in range(20):
            time.sleep(15) # перевіряємо кожні 15 секунд
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

        # 3. Розпаковуємо ZIP і читаємо Excel прямо в оперативній пам'яті
        self.stdout.write(self.style.WARNING("2️⃣ Розпакування та аналіз прайсу..."))
        try:
            with zipfile.ZipFile(io.BytesIO(file_content)) as z:
                filename = z.namelist()[0]
                with z.open(filename) as f:
                    # УВАГА: Пропускаємо перші 8 рядків (синя шапка на 9-му рядку)
                    df = pd.read_excel(f, sheet_name='Шини Легкові', skiprows=8, engine='xlrd')
            
            # Очищаємо назви колонок від випадкових пробілів та переносів рядків
            df.columns = df.columns.str.strip().str.replace('\n', ' ')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Помилка читання Excel: {e}"))
            return

        # Перевіряємо, чи є потрібні колонки
        if 'Товар' not in df.columns or 'Загальний залишок' not in df.columns:
            self.stdout.write(self.style.ERROR(f"❌ Не знайдено потрібних колонок у прайсі!"))
            self.stdout.write(self.style.ERROR(f"🔍 Знайдені колонки: {list(df.columns)}"))
            return

        self.stdout.write(self.style.SUCCESS(f"📊 Знайдено {len(df)} рядків товарів. Починаємо оновлення бази..."))

        # 4. Оновлюємо базу даних
        updated_count = 0
        not_found_count = 0

        # Спочатку обнуляємо всі залишки на сайті
        Product.objects.update(stock_quantity=0)

        with transaction.atomic():
            for index, row in df.iterrows():
                name_in_excel = str(row.get('Товар', '')).strip()
                
                if not name_in_excel or name_in_excel == 'nan':
                    continue

                # Очищаємо залишок (якщо написано '>20', робимо просто 20)
                raw_stock = str(row.get('Загальний залишок', '0')).replace('>', '').replace('<', '').strip()
                try:
                    stock = int(float(raw_stock))
                except ValueError:
                    stock = 0

                # Очищаємо ціну (беремо колонку 'Інтернет ціна')
                raw_price = str(row.get('Інтернет ціна', '0')).replace(' ', '').replace(',', '.').strip()
                try:
                    price = float(raw_price)
                except ValueError:
                    price = 0.0

                product = Product.objects.filter(name__iexact=name_in_excel).first()
                
                if product:
                    product.stock_quantity = stock
                    if price > 0:
                        product.price = price
                    product.save()
                    updated_count += 1
                else:
                    not_found_count += 1

        self.stdout.write(self.style.SUCCESS(f"\n🎉 ГОТОВО! Оновлено товарів: {updated_count}"))
        self.stdout.write(self.style.WARNING(f"⚠️ Не знайдено збігів по назві: {not_found_count}"))
