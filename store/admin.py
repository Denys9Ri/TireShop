from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django import forms
import openpyxl
import re
from .models import Product, Brand

# --- ФОРМА ДЛЯ ЗАВАНТАЖЕННЯ ---
class ExcelImportForm(forms.Form):
    excel_file = forms.FileField()

# --- ГОЛОВНИЙ КЛАС АДМІНКИ ---
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # Що показувати в таблиці
    list_display = ['name', 'brand', 'width', 'profile', 'diameter', 'price_display', 'stock_quantity']
    list_filter = ['brand', 'seasonality', 'diameter']
    search_fields = ['name', 'width']
    change_list_template = "store/admin_changelist.html"

    # Відображення ціни продажу (+30%)
    def price_display(self, obj):
        return obj.price
    price_display.short_description = "Ціна (+30%)"

    # Додаємо URL для імпорту
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-excel/', self.import_excel, name="import_excel"),
        ]
        return my_urls + urls

    # --- ЛОГІКА ІМПОРТУ ---
    def import_excel(self, request):
        if request.method == "POST":
            excel_file = request.FILES["excel_file"]
            try:
                # Відкриваємо файл в режимі "Тільки читання" (економить пам'ять)
                wb = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
                sheet = wb.active
                
                # Лічильники для статистики
                created_count = 0
                updated_count = 0
                skipped_count = 0
                
                # Проходимо по кожному рядку (починаючи з 2-го)
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    # Перевірка: якщо Бренд і Модель пусті - пропускаємо
                    if not row[0] and not row[1]:
                        skipped_count += 1
                        continue

                    # --- 1. БРЕНД (Колонка A / 0) ---
                    brand_name = str(row[0]).strip() if row[0] else "Unknown"
                    brand_obj, _ = Brand.objects.get_or_create(name=brand_name)

                    # --- 2. РОЗМІР (Колонка C / 2) ---
                    size_str = str(row[2]).strip() if row[2] else ""
                    # Шукаємо цифри: 205/55 R16
                    match = re.search(r'(\d+)/(\d+)\s*[a-zA-Z]*\s*(\d+)', size_str)
                    
                    size_is_valid = False
                    if match:
                        width = int(match.group(1))
                        profile = int(match.group(2))
                        diameter = int(match.group(3))
                        size_is_valid = True
                    else:
                        width = 0
                        profile = 0
                        diameter = 0

                    # --- 3. МОДЕЛЬ ТА УНІКАЛЬНІСТЬ (Колонка B / 1) ---
                    model_name = str(row[1]).strip() if row[1] else "Model"
                    
                    # Якщо розмір не розпізнали, додаємо його текст в назву,
                    # щоб різні шини з "кривим" розміром не перезаписували одна одну.
                    unique_model_name = model_name
                    if not size_is_valid and size_str:
                         unique_model_name = f"{model_name} [{size_str}]"

                    # --- 4. СЕЗОН (Колонка D / 3) ---
                    season_raw = str(row[3]).lower() if row[3] else ""
                    season_key = 'all-season'
                    if 'зим' in season_raw or 'winter' in season_raw:
                        season_key = 'winter'
                    elif 'літ' in season_raw or 'лет' in season_raw or 'summer' in season_raw:
                        season_key = 'summer'

                    # --- 5. ЦІНА (Колонка E / 4) - РОЗУМНА ОБРОБКА ---
                    raw_val = row[4]
                    val_str = str(raw_val) if raw_val is not None else ""
                    
                    # Чистка сміття: коми на крапки, прибираємо пробіли
                    val_str = val_str.replace(',', '.')
                    val_str = val_str.replace(' ', '').replace('\xa0', '') # \xa0 - це невидимий пробіл
                    val_str = val_str.replace('грн', '').replace('uah', '')
                    
                    try:
                        raw_cost = float(val_str)
                    except:
                        raw_cost = 0.0

                    # --- 6. КІЛЬКІСТЬ (Колонка F / 5) ---
                    try:
                        qty = int(row[5]) if row[5] is not None else 0
                    except:
                        qty = 0

                    # Опис для картки товару
                    full_description = f"Шини {brand_name} {model_name}. {size_str}. Сезон: {season_raw}."

                    # --- 7. ЗАПИС АБО ОНОВЛЕННЯ ---
                    obj, created = Product.objects.update_or_create(
                        name=unique_model_name,
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
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                
                # Повідомлення про успіх
                total = created_count + updated_count
                msg = (f"🏁 ОБРОБЛЕНО: {total}. "
                       f"✅ Нових: {created_count}. "
                       f"🔄 Оновлено: {updated_count}. "
                       f"❌ Пропущено: {skipped_count}.")
                messages.success(request, msg)

            except Exception as e:
                messages.error(request, f'Критична помилка імпорту: {e}')
                
            return redirect("..")
            
        form = ExcelImportForm()
        return render(request, "store/admin_import.html", {"form": form})

# Реєструємо бренд окремо
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name']
