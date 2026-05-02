import requests
import os
import re
import time
from django.core.management.base import BaseCommand
from store.models import Product, Brand
from django import db

class Command(BaseCommand):
    help = 'GOLD Посторінкова синхронізація через пряме API Омега (Універсальна)'

    def handle(self, *args, **options):
        KEY = os.environ.get("OMEGA_API_KEY", "ORMX5xgdRK5aqkFU8nlKfRv1rtnJmwc7")
        url = "https://public.omega.page/public/api/v1.0/searchcatalog/getTires"
        
        self.stdout.write(self.style.WARNING("🚀 Запуск універсальної GOLD-синхронізації..."))

        # Скидаємо залишки перед оновленням
        Product.objects.update(stock_quantity=0)

        updated_count = 0
        created_count = 0
        current_from = 0
        batch_size = 1000 

        while True:
            self.stdout.write(f"📥 Завантаження товарів з позиції {current_from}...")
            
            # Прибираємо UsageList, щоб API точно віддало список
            payload = {
                "From": current_from,
                "Count": batch_size,
                "Key": KEY
            }

            try:
                response = requests.post(url, json=payload, timeout=60)
                data = response.json()
                
                if not data.get('Success'):
                    self.stdout.write(self.style.ERROR(f"❌ Помилка API: {data.get('Errors')}"))
                    break

                result_data = data.get('Data', {})
                items = result_data.get('Result', [])
                total_available = result_data.get('Total', 0)

                if not items:
                    self.stdout.write("ℹ️ Товарів більше немає.")
                    break

                for item in items:
                    name_omega = item.get('DescriptionUkr', '')
                    if not name_omega: continue

                    # Фільтруємо тільки шини (на випадок, якщо API підкине запчастини)
                    if "Шина" not in name_omega: continue

                    brand_name = item.get('BrandDescription', 'Unknown')
                    price_omega = item.get('CustomerPrice', 0)
                    image_url = item.get('ImageUrl', '')
                    
                    # Розрахунок залишку
                    total_stock = 0
                    for rest in item.get('Rests', []):
                        val = str(rest.get('Value', '0')).replace('>', '')
                        try:
                            total_stock += int(val)
                        except: continue
                    
                    if total_stock > 20: total_stock = 20

                    # Парсинг розмірів
                    size_match = re.search(r'(\d{3})/(\d{2,3})\s?[R|r](\d{2})', name_omega)
                    w = int(size_match.group(1)) if size_match else 0
                    p = int(size_match.group(2)) if size_match else 0
                    d = int(size_match.group(3)) if size_match else 0

                    clean_name = name_omega.replace('Шина ', '').strip()
                    
                    # Шукаємо в базі (спершу по точному імені, потім по Slug, якщо потрібно)
                    product = Product.objects.filter(name__iexact=clean_name).first()
                    if not product:
                        product = Product.objects.filter(name__iexact=name_omega).first()

                    if product:
                        product.stock_quantity = total_stock
                        product.cost_price = price_omega
                        product.description = item.get('Info', '')
                        
                        if image_url and (not product.photo or product.photo == ''):
                            product.photo_url = image_url
                        
                        product.price = 0 
                        product.save()
                        updated_count += 1
                    else:
                        brand_obj, _ = Brand.objects.get_or_create(name=brand_name)
                        Product.objects.create(
                            name=clean_name,
                            brand=brand_obj,
                            width=w, profile=p, diameter=d,
                            cost_price=price_omega,
                            stock_quantity=total_stock,
                            description=item.get('Info', ''),
                            photo_url=image_url
                        )
                        created_count += 1

                current_from += batch_size
                db.reset_queries()
                
                if current_from >= total_available or current_from >= 5000: # Обмежувач безпеки
                    break
                
                time.sleep(0.5)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"💥 Помилка: {e}"))
                break

        self.stdout.write(self.style.SUCCESS(f"\n🎉 GOLD-Синхронізація завершена!"))
        self.stdout.write(self.style.SUCCESS(f"🔄 Оновлено: {updated_count}"))
        self.stdout.write(self.style.SUCCESS(f"➕ Створено: {created_count}"))
