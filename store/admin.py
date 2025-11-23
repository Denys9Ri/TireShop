from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django import forms
import openpyxl
import re
# Додаємо імпорт Order та OrderItem
from .models import Product, Brand, Order, OrderItem

# --------------------------------------------------------
# 1. ЗАМОВЛЕННЯ (ТЕ, ЩО ЗНИКЛО)
# --------------------------------------------------------

# Дозволяє бачити товари прямо всередині замовлення
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product'] # Щоб зручно шукати товар, якщо їх тисячі
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Колонки, які ви бачите в списку
    list_display = ['id', 'status', 'created_at', 'full_name', 'phone', 'shipping_type', 'total_cost']
    # Фільтри збоку (дуже зручно)
    list_filter = ['status', 'created_at', 'shipping_type']
    # Пошук
    search_fields = ['id', 'full_name', 'phone', 'email']
    # Включаємо товари в картку замовлення
    inlines = [OrderItemInline]
    # Дозволяє змінювати статус прямо із загального списку (опціонально)
    list_editable = ['status']

    # Додаткова колонка: Загальна сума замовлення
    def total_cost(self, obj):
        return sum(item.get_cost() for item in obj.items.all())
    total_cost.short_description = 'Сума'

# --------------------------------------------------------
# 2. ТОВАРИ ТА ІМПОРТ EXCEL (ОПТИМІЗОВАНИЙ)
# --------------------------------------------------------

class ExcelImportForm(forms.Form):
    excel_file = forms.FileField()

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'width', 'profile', 'diameter', 'price_display', 'stock_quantity']
    list_filter = ['brand', 'seasonality', 'diameter']
    search_fields = ['name', 'width']
    change_list_template = "store/admin_changelist.html"

    def price_display(self, obj):
        return obj.price
    price_display.short_description = "Ціна (+30%)"

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
                # Читаємо файл економно (read_only=True)
                wb = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
                sheet = wb.active
                
                created_count = 0
                updated_count = 0
                skipped_count = 0
                
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    # Пропускаємо пусті рядки
                    if not row[0] and not row[1]:
                        skipped_count += 1
                        continue

                    # --- БРЕНД ---
                    brand_name = str(row[0]).strip() if row[0] else "Unknown"
                    brand_obj, _ = Brand.objects.get_or_create(name=brand_name)

                    # --- РОЗМІР ---
                    size_str = str(row[2]).strip() if row[2] else ""
                    match = re.search(r'(\d+)/(\d+)\s*[a-zA-Z]*\s*(\d+)', size_str)
                    
                    size_is_valid = False
                    if match:
                        width = int(match.group(1))
                        profile = int(match.group(2))
                        diameter = int(match.group(3))
                        size_is_valid = True
                    else:
                        width = 0; profile = 0; diameter = 0

                    # --- МОДЕЛЬ ---
                    model_name = str(row[1]).strip() if row[1] else "Model"
                    unique_model_name = model_name
                    if not size_is_valid and size_str:
                         unique_model_name = f"{model_name} [{size_str}]"

                    # --- СЕЗОН ---
                    season_raw = str(row[3]).lower() if row[3] else ""
                    season_key = 'all-season'
                    if 'зим' in season_raw or 'winter' in season_raw: season_key = 'winter'
                    elif 'літ' in season_raw or 'лет' in season_raw or 'summer' in season_raw: season_key = 'summer'

                    # --- ЦІНА ---
                    raw_val = row[4]
                    val_str = str(raw_val) if raw_val is not None else ""
                    val_str = val_str.replace(',', '.').replace(' ', '').replace('\xa0', '').replace('грн', '')
                    try: raw_cost = float(val_str)
                    except: raw_cost = 0.0

                    # --- КІЛЬКІСТЬ ---
                    try: qty = int(row[5]) if row[5] is not None else 0
                    except: qty = 0

                    full_description = f"Шини {brand_name} {model_name}. {size_str}. Сезон: {season_raw}."

                    # --- ЗАПИС ---
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
                    
                    if created: created_count += 1
                    else: updated_count += 1
                
                msg = f"ОБРОБЛЕНО. ✅ Нових: {created_count}. 🔄 Оновлено: {updated_count}. ❌ Пропущено: {skipped_count}."
                messages.success(request, msg)

            except Exception as e:
                messages.error(request, f'Помилка імпорту: {e}')
                
            return redirect("..")
            
        form = ExcelImportForm()
        return render(request, "store/admin_import.html", {"form": form})

# --------------------------------------------------------
# 3. БРЕНДИ
# --------------------------------------------------------
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name']
