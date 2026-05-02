import requests
import os
import re
from django.core.management.base import BaseCommand
from store.models import Product, Brand
from django import db

class Command(BaseCommand):
    help = 'GOLD Синхронізація через пряме API Омега (без Excel)'

    def handle(self, *args, **options):
        KEY = os.environ.get("OMEGA_API_KEY", "ORMX5xgdRK5aqkFU8nlKfRv1rtnJmwc7")
        url = "https://public.omega.page/public/api/v1.0/searchcatalog/getTires"
        
        self.stdout.write(self.style.WARNING("🚀 Запуск GOLD-синхронізації..."))

        # Запитуємо дані (беремо 5000 позицій одним махом)
        payload = {
            "UsageList": ["Легковая"],
            "Count": 5000,
            "Key": KEY
        }

        try:
            response = requests.post(url, json=payload, timeout=60)
            data = response.json()
            
            if not data.get('Success'):
                self.stdout.write(self.style.ERROR(f"❌ Помилка API: {data.get('Errors')}"))
                return

            items = data.get('Data', {}).get('Result', [])
            total = len(items)
            self.stdout.write(self.style.SUCCESS(f"✅ Отримано {total} товарів з API"))

            # Скидаємо залишки перед оновленням
            Product.objects.update(stock_quantity=0)

            updated_count = 0
            created_count = 0

            for item in items:
                name_omega = item.get('DescriptionUkr', '')
                brand_name = item.get('BrandDescription', 'Unknown')
                price_omega = item.get('CustomerPrice', 0) # Твоя вхідна ціна
                
                # Рахуємо загальний залишок по всіх складах
                total_stock = 0
                for rest in item.get('Rests', []):
                    val = rest.get('Value', '0')
                    if '>' in val: val = val.replace('>', '')
                    total_stock += int(val)
                
                if total_stock > 20: total_stock = 20

                # Витягуємо параметри з назви (напр. 215/75R16)
                size_match = re.search(r'(\d{3})/(\d{2,3})[R|r](\d{2})', name_omega)
                w = int(size_match.group(1)) if size_match else 0
                p = int(size_match.group(2)) if size_match else 0
                d = int(size_match.group(3)) if size_match else 0

                # Шукаємо товар в базі
                clean_name = name_omega.replace('Шина ', '').strip()
                product = Product.objects.filter(name__iexact=clean_name).first()
                
                if not product:
                    product = Product.objects.filter(name__iexact=name_omega).first()

                if product:
                    product.stock_quantity = total_stock
                    product.cost_price = price_omega # Записуємо собівартість
                    product.description = item.get('Info', '') # Опис з HTML
                    product.price = 0 # Обнуляємо, щоб спрацювала твоя націнка 1.30 у models.py
                    product.save()
                    updated_count += 1
                else:
                    # Якщо товару немає - створюємо
                    brand_obj, _ = Brand.objects.get_or_create(name=brand_name)
                    Product.objects.create(
                        name=clean_name,
                        brand=brand_obj,
                        width=w, profile=p, diameter=d,
                        cost_price=price_omega,
                        stock_quantity=total_stock,
                        description=item.get('Info', '')
                    )
                    created_count += 1

                if updated_count % 100 == 0:
                    self.stdout.write(f"⚙️ Опрацьовано {updated_count}...")
                    db.reset_queries()

            self.stdout.write(self.style.SUCCESS(f"\n🎉 ПЕРЕМОГА! Оновлено: {updated_count}, Створено: {created_count}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"💥 Критична помилка: {e}"))
