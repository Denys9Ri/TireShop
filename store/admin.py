from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django import forms
import openpyxl
import re
from .models import Product, Brand, Order, OrderItem

# --- ЗАМОВЛЕННЯ ---
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'created_at', 'full_name', 'phone', 'shipping_type', 'total_cost']
    list_filter = ['status', 'created_at', 'shipping_type']
    search_fields = ['id', 'full_name', 'phone', 'email']
    inlines = [OrderItemInline]
    list_editable = ['status']
    
    def total_cost(self, obj):
        return sum(item.get_cost() for item in obj.items.all())
    total_cost.short_description = 'Сума'

# --- ТОВАРИ ТА ІМПОРТ ---
class ExcelImportForm(forms.Form):
    excel_file = forms.FileField()

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'width', 'profile', 'diameter', 'country', 'year', 'price_display', 'stock_quantity']
    list_filter = ['brand', 'seasonality', 'diameter', 'stud_type'] # Додали фільтр по шипам
    search_fields = ['name', 'width']
    change_list_template = "store/admin_changelist.html"

    def price_display(self, obj):
        return obj.price
    price_display.short_description = "Ціна (+30%)"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('import-excel/', self.import_excel, name="import_excel")]
        return my_urls + urls

    def import_excel(self, request):
        if request.method == "POST":
            excel_file = request.FILES["excel_file"]
            try:
                wb = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
                sheet = wb.active
                
                created_count = 0
                updated_count = 0
                skipped_count = 0
                
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    if not row[0] and not row[1]:
                        skipped_count += 1
                        continue

                    # 1. Основні дані
                    brand_name = str(row[0]).strip() if row[0] else "Unknown"
                    brand_obj, _ = Brand.objects.get_or_create(name=brand_name)
                    
                    model_name = str(row[1]).strip() if row[1] else "Model"
                    
                    # 2. Розмір
                    size_str = str(row[2]).strip() if row[2] else ""
                    match = re.search(r'(\d+)/(\d+)\s*[a-zA-Z]*\s*(\d+)', size_str)
                    size_valid = False
                    if match:
                        width = int(match.group(1))
                        profile = int(match.group(2))
                        diameter = int(match.group(3))
                        size_valid = True
                    else:
                        width=0; profile=0; diameter=0

                    unique_model_name = model_name
                    if not size_valid and size_str:
                         unique_model_name = f"{model_name} [{size_str}]"

                    # 3. Сезон
                    season_raw = str(row[3]).lower() if row[3] else ""
                    season_key = 'all-season'
                    if 'зим' in season_raw or 'winter' in season_raw: season_key = 'winter'
                    elif 'літ' in season_raw or 'лет' in season_raw or 'summer' in season_raw: season_key = 'summer'

                    # 4. Ціна та Кількість
                    try:
                        val_str = str(row[4]).replace(',', '.').replace(' ', '').replace('\xa0', '').replace('грн', '')
                        raw_cost = float(val_str)
                    except: raw_cost = 0.0
                    
                    try: qty = int(row[5]) if row[5] is not None else 0
                    except: qty = 0

                    # --- 5. НОВІ ПОЛЯ (G, H, I, J, K, L) ---
                    # row[6] - Країна
                    country_val = str(row[6]).strip() if len(row) > 6 and row[6] else "-"
                    
                    # row[7] - Рік
                    try: year_val = int(row[7]) if len(row) > 7 and row[7] else 2024
                    except: year_val = 2024
                    
                    # row[8] - Індекс Навантаження
                    load_val = str(row[8]).strip() if len(row) > 8 and row[8] else "-"
                    
                    # row[9] - Індекс Швидкості
                    speed_val = str(row[9]).strip() if len(row) > 9 and row[9] else "-"
                    
                    # row[10] - Шипи
                    stud_val = str(row[10]).strip() if len(row) > 10 and row[10] else "Не шип"
                    
                    # row[11] - Тип авто
                    vehicle_val = str(row[11]).strip() if len(row) > 11 and row[11] else "Легковий"


                    # Формуємо красивий опис (Description)
                    full_desc = (f"Шини {brand_name} {model_name}. Розмір: {size_str}. "
                                 f"Сезон: {season_raw}. Виробництво: {country_val} {year_val}.")

                    # ЗАПИС
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
                            'description': full_desc,
                            # Нові поля:
                            'country': country_val,
                            'year': year_val,
                            'load_index': load_val,
                            'speed_index': speed_val,
                            'stud_type': stud_val,
                            'vehicle_type': vehicle_val,
                        }
                    )
                    
                    if created: created_count += 1
                    else: updated_count += 1
                
                messages.success(request, f"ОБРОБЛЕНО. ✅ Нових: {created_count}. 🔄 Оновлено: {updated_count}.")
            except Exception as e:
                messages.error(request, f'Помилка імпорту: {e}')
            return redirect("..")
        form = ExcelImportForm()
        return render(request, "store/admin_import.html", {"form": form})

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name']
