from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django import forms
import openpyxl # Використовуємо пряму бібліотеку замість важкої pandas
import re
from .models import Product, Brand

# Форма для файлу
class ExcelImportForm(forms.Form):
    excel_file = forms.FileField()

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'width', 'profile', 'diameter', 'cost_price', 'price_display']
    list_filter = ['brand', 'seasonality', 'diameter']
    search_fields = ['name', 'width']
    change_list_template = "store/admin_changelist.html"

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
                # ВМИКАЄМО РЕЖИМ ЕКОНОМІЇ ПАМ'ЯТІ (read_only=True)
                wb = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
                sheet = wb.active
                
                count = 0
                # Пропускаємо заголовок (min_row=2) і читаємо рядки
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    # row - це кортеж значень (0, 1, 2, 3, 4, 5...)
                    # 0=Бренд, 1=Модель, 2=Типоразмер, 3=Сезон, 4=Цена, 5=Кол-во
                    
                    # Якщо рядок пустий - пропускаємо
                    if not row[0] and not row[1]:
                        continue

                    # --- 1. БРЕНД ---
                    brand_name = str(row[0]).strip() if row[0] else "Unknown"
                    brand_obj, _ = Brand.objects.get_or_create(name=brand_name)

                    # --- 2. РОЗМІР ---
                    size_str = str(row[2]).strip() if row[2] else ""
                    match = re.search(r'(\d+)/(\d+)\s*[a-zA-Z]*\s*(\d+)', size_str)
                    
                    if match:
                        width = int(match.group(1))
                        profile = int(match.group(2))
                        diameter = int(match.group(3))
                    else:
                        width = 0
                        profile = 0
                        diameter = 0

                    # --- 3. СЕЗОН ---
                    season_raw = str(row[3]).lower() if row[3] else ""
                    season_key = 'all-season'
                    if 'зим' in season_raw or 'winter' in season_raw:
                        season_key = 'winter'
                    elif 'літ' in season_raw or 'лет' in season_raw or 'summer' in season_raw:
                        season_key = 'summer'

                    # --- 4. ЦІНА ---
                    try:
                        raw_cost = float(row[4]) if row[4] else 0.0
                    except:
                        raw_cost = 0.0

                    # --- 5. КІЛЬКІСТЬ ---
                    try:
                        qty = int(row[5]) if row[5] is not None else 0
                    except:
                        qty = 0

                    # --- 6. ЗАПИС ---
                    model_name = str(row[1]).strip() if row[1] else "Model"
                    
                    # Створюємо назву для опису
                    full_description = f"Шини {brand_name} {model_name}. {size_str}. Сезон: {season_raw}."

                    Product.objects.update_or_create(
                        name=model_name,
                        brand=brand_obj,
                        width=width,
                        profile=profile,
                        diameter=diameter,
                        defaults={
                            'seasonality': season_key,
                            'cost_price': raw_cost,
                            'stock_quantity': qty,
                            'description': full_description
                        }
                    )
                    count += 1
                
                messages.success(request, f'Успішно оброблено {count} товарів! (Економний режим)')

            except Exception as e:
                messages.error(request, f'Помилка: {e}')
                
            return redirect("..")
            
        form = ExcelImportForm()
        return render(request, "store/admin_import.html", {"form": form})

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name']
