from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django import forms
import pandas as pd
import re # Бібліотека для пошуку цифр у тексті
from .models import Product, Brand

# Форма для файлу
class ExcelImportForm(forms.Form):
    excel_file = forms.FileField()

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # Показуємо корисні колонки в адмінці
    list_display = ['name', 'brand', 'width', 'profile', 'diameter', 'cost_price', 'price_display']
    list_filter = ['brand', 'seasonality', 'diameter']
    search_fields = ['name', 'width']
    change_list_template = "store/admin_changelist.html"

    # Додаткова колонка, щоб бачити ціну продажу (обчислену)
    def price_display(self, obj):
        return obj.price
    price_display.short_description = "Ціна продажу (+30%)"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-excel/', self.import_excel, name="import_excel"),
        ]
        return my_urls + urls

    def import_excel(self, request):
        if request.method == "POST":
            excel_file = request.FILES["excel_file"]
            try:
                df = pd.read_excel(excel_file)
                df = df.fillna('') # Забираємо пусті значення
                
                count = 0
                for index, row in df.iterrows():
                    # --- 1. ОБРОБКА БРЕНДУ ---
                    brand_name = str(row['Бренд']).strip()
                    # get_or_create повертає (об'єкт, чи_створено)
                    brand_obj, _ = Brand.objects.get_or_create(name=brand_name)

                    # --- 2. ОБРОБКА РОЗМІРУ (напр. "205/55 R16") ---
                    size_str = str(row['Типоразмер']).strip()
                    
                    # Шукаємо 3 групи цифр. R16 або Z16 або просто 16
                    # Цей вираз шукає: (число) / (число) (будь-яка літера) (число)
                    match = re.search(r'(\d+)/(\d+)\s*[a-zA-Z]*\s*(\d+)', size_str)
                    
                    if match:
                        width = int(match.group(1))   # 205
                        profile = int(match.group(2)) # 55
                        diameter = int(match.group(3))# 16
                    else:
                        # Якщо розмір кривий, ставимо нулі, щоб не ламалось
                        width = 0
                        profile = 0
                        diameter = 0

                    # --- 3. ОБРОБКА СЕЗОНУ ---
                    season_raw = str(row['Сезон']).lower()
                    season_key = 'all-season' # За замовчуванням
                    
                    if 'зим' in season_raw or 'winter' in season_raw:
                        season_key = 'winter'
                    elif 'літ' in season_raw or 'лет' in season_raw or 'summer' in season_raw:
                        season_key = 'summer'

                    # --- 4. ЦІНА (З Excel беремо ціну закупки) ---
                    try:
                        raw_cost = float(row['Цена'])
                    except:
                        raw_cost = 0.0

                    # --- 5. КІЛЬКІСТЬ ---
                    try:
                        qty = int(row['Кол-во'])
                    except:
                        qty = 0

                    # --- 6. ЗАПИС У БАЗУ ---
                    # Ми шукаємо товар за Моделлю, Брендом і Розміром.
                    # Якщо такий є - оновлюємо ціну і кількість. Якщо немає - створюємо.
                    
                    model_name = str(row['Модель']).strip()

                    Product.objects.update_or_create(
                        name=model_name,
                        brand=brand_obj,
                        width=width,
                        profile=profile,
                        diameter=diameter,
                        defaults={
                            'seasonality': season_key,
                            'cost_price': raw_cost, # Зберігаємо ціну закупки
                            'stock_quantity': qty,
                            'description': f"Шини {brand_name} {model_name}. {size_str}. Сезон: {season_raw}."
                        }
                    )
                    count += 1
                
                messages.success(request, f'Успішно оброблено {count} товарів!')

            except Exception as e:
                messages.error(request, f'Помилка: {e}')
                
            return redirect("..")
            
        form = ExcelImportForm()
        return render(request, "store/admin_import.html", {"form": form})

# Не забудьте зареєструвати модель Brand, щоб додавати бренди вручну, якщо треба
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name']
