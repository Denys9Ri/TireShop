from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django import forms
import openpyxl
import re
from django.utils.html import format_html
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
    list_display = ['name', 'brand', 'width', 'profile', 'diameter', 'country', 'year', 'price_display', 'stock_quantity', 'photo_preview']
    list_filter = ['brand', 'seasonality', 'diameter', 'stud_type']
    search_fields = ['name', 'width']
    change_list_template = "store/admin_changelist.html"
    readonly_fields = ["photo_preview"]

    fieldsets = (
        (None, {
            'fields': (
                'name', 'brand', 'width', 'profile', 'diameter', 'seasonality',
                'description'
            )
        }),
        ('Ціни та наявність', {
            'fields': ('cost_price', 'stock_quantity')
        }),
        ('Головне фото', {
            'fields': ('photo', 'photo_url', 'photo_preview'),
            'description': 'Додайте пряме посилання на фото (photo_url), щоб воно одразу відобразилось на сайті, або завантажте файл.'
        }),
        ('Характеристики', {
            'fields': ('country', 'year', 'load_index', 'speed_index', 'stud_type', 'vehicle_type')
        }),
    )

    def price_display(self, obj):
        return obj.price
    price_display.short_description = "Ціна (+30%)"

    def photo_preview(self, obj):
        if obj.photo_url:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px; border-radius: 4px;"/>', obj.photo_url)
        if obj.photo:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px; border-radius: 4px;"/>', obj.photo.url)
        return "—"
    photo_preview.short_description = "Фото"

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

                rows_iter = sheet.iter_rows(values_only=True)
                try:
                    header_row = next(rows_iter)
                except StopIteration:
                    messages.error(request, "Файл порожній.")
                    return redirect("..")

                def find_column(aliases):
                    for idx, cell in enumerate(header_row):
                        cell_val = str(cell or "").strip().lower()
                        for alias in aliases:
                            if cell_val.startswith(alias):
                                return idx
                    return None

                col_brand = find_column(["бренд", "brand", "фірма", "марка"])
                col_model = find_column(["модель", "model", "назва", "название"])
                col_size = find_column(["типоразмер", "типорозмір", "размер", "size"])
                col_season = find_column(["сезон", "season", "сезонність"])
                col_price = find_column(["цена", "price", "варт", "cost"])
                col_qty = find_column(["кол", "кільк", "qty", "шт"])
                col_country = find_column(["країна", "страна", "country"])
                col_year = find_column(["рік", "год", "year"])
                col_load = find_column(["індекс нав", "нагруз", "load"])
                col_speed = find_column(["індекс швид", "скор", "speed"])
                col_stud = find_column(["шип", "stud"])
                col_vehicle = find_column(["тип авто", "авто", "vehicle"])
                col_photo = find_column(["фото", "photo", "image"])

                # Фолбеки (якщо заголовки не знайдено, використовуємо стандартні номери колонок)
                col_brand = 0 if col_brand is None else col_brand
                col_model = 1 if col_model is None else col_model
                col_size = 2 if col_size is None else col_size
                col_season = 3 if col_season is None else col_season
                col_price = 4 if col_price is None else col_price
                col_qty = 5 if col_qty is None else col_qty

                for row in rows_iter:
                    if not any(row):
                        skipped_count += 1
                        continue

                    # 1. Основні дані
                    brand_raw = row[col_brand] if col_brand is not None and len(row) > col_brand else None
                    brand_name = str(brand_raw).strip() if brand_raw else ""

                    model_raw = row[col_model] if col_model is not None and len(row) > col_model else None
                    model_name = str(model_raw).strip() if model_raw else ""

                    if not brand_name and not model_name:
                        skipped_count += 1
                        continue

                    if not brand_name: brand_name = "Unknown"
                    if not model_name: model_name = "Model"

                    brand_obj, _ = Brand.objects.get_or_create(name=brand_name)

                    # 2. Розмір
                    size_raw = row[col_size] if col_size is not None and len(row) > col_size else ""
                    size_str = str(size_raw).strip() if size_raw else ""
                    match = re.search(r'(\d+)/(\d+)\s*[a-zA-Z]*\s*(\d+)', size_str)
                    
                    size_valid = False
                    if match:
                        width = int(match.group(1))
                        profile = int(match.group(2))
                        diameter = int(match.group(3))
                        size_valid = True
                    else:
                        width = 0; profile = 0; diameter = 0

                    unique_model_name = model_name
                    if not size_valid and size_str:
                        unique_model_name = f"{model_name} [{size_str}]"

                    # 3. Сезон
                    season_raw = row[col_season] if col_season is not None and len(row) > col_season else ""
                    season_raw_str = str(season_raw).lower() if season_raw else ""
                    season_key = 'all-season'
                    if 'зим' in season_raw_str or 'winter' in season_raw_str: season_key = 'winter'
                    elif 'літ' in season_raw_str or 'лет' in season_raw_str or 'summer' in season_raw_str: season_key = 'summer'

                    # --- 4. ЦІНА (БРОНЕБІЙНА ЛОГІКА) ---
                    raw_val = row[col_price] if col_price is not None and len(row) > col_price else None

                    if isinstance(raw_val, (int, float)):
                        raw_cost = float(raw_val)
                    else:
                        val_str = str(raw_val) if raw_val is not None else ""
                        # Чистимо від усього крім цифр, крапок і ком
                        val_str = re.sub(r'[^\d,.]', '', val_str)
                        val_str = val_str.replace(',', '.')
                        
                        # Фікс для 1.200.00 (забагато крапок)
                        if val_str.count('.') > 1:
                            parts = val_str.split('.')
                            val_str = "".join(parts[:-1]) + "." + parts[-1]
                        
                        try:
                            raw_cost = float(val_str)
                        except ValueError:
                            raw_cost = 0.0

                    # 5. Кількість
                    qty_cell = row[col_qty] if col_qty is not None and len(row) > col_qty else 0
                    try:
                        qty_str = str(qty_cell).strip()
                        if qty_str == '>12': qty = 20
                        elif qty_str.isdigit(): qty = int(qty_str)
                        else: qty = int(re.sub(r'[^0-9]', '', qty_str) or 0)
                    except: qty = 0

                    # 6. Додаткові характеристики
                    country_val = str(row[col_country]).strip() if col_country is not None and len(row) > col_country and row[col_country] else "-"
                    
                    try:
                        year_val = int(row[col_year]) if col_year is not None and len(row) > col_year and row[col_year] else 2024
                    except: year_val = 2024

                    load_val = str(row[col_load]).strip() if col_load is not None and len(row) > col_load and row[col_load] else "-"
                    speed_val = str(row[col_speed]).strip() if col_speed is not None and len(row) > col_speed and row[col_speed] else "-"
                    stud_val = str(row[col_stud]).strip() if col_stud is not None and len(row) > col_stud and row[col_stud] else "Не шип"
                    vehicle_val = str(row[col_vehicle]).strip() if col_vehicle is not None and len(row) > col_vehicle and row[col_vehicle] else "Легковий"
                    
                    photo_url_val = str(row[col_photo]).strip() if col_photo is not None and len(row) > col_photo and row[col_photo] else None

                    full_desc = (f"Шини {brand_name} {model_name}. Розмір: {size_str}. "
                                 f"Сезон: {season_raw_str}. Виробництво: {country_val} {year_val}.")

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
                            'country': country_val,
                            'year': year_val,
                            'load_index': load_val,
                            'speed_index': speed_val,
                            'stud_type': stud_val,
                            'vehicle_type': vehicle_val,
                        }
                    )

                    if photo_url_val and not obj.photo_url:
                        obj.photo_url = photo_url_val
                        obj.save(update_fields=["photo_url"])

                    if created: created_count += 1
                    else: updated_count += 1

                messages.success(request, f"ОБРОБЛЕНО. ✅ Нових: {created_count}. 🔄 Оновлено: {updated_count}. Пропущено: {skipped_count}.")
            except Exception as e:
                messages.error(request, f'Помилка імпорту: {e}')
            return redirect("..")
        form = ExcelImportForm()
        return render(request, "store/admin_import.html", {"form": form})

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name']
