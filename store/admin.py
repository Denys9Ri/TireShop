from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django import forms
import openpyxl
import re
import gc # <--- Імпорт для очищення пам'яті
from django.utils.html import format_html
from .models import Product, Brand, Order, OrderItem, SiteBanner, ProductImage

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

# --- ГАЛЕРЕЯ ФОТО ---
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image_url', 'image', 'preview')
    readonly_fields = ('preview',)

    def preview(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="height: 50px; border-radius: 4px;"/>', obj.image_url)
        if obj.image:
            return format_html('<img src="{}" style="height: 50px; border-radius: 4px;"/>', obj.image.url)
        return "-"

# --- ТОВАРИ ТА ІМПОРТ ---
class ExcelImportForm(forms.Form):
    excel_file = forms.FileField()

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'width', 'profile', 'diameter', 'price_display', 'stock_quantity', 'year', 'photo_preview']
    list_filter = ['brand', 'seasonality', 'diameter']
    search_fields = ['name', 'width', 'brand__name']
    change_list_template = "store/admin_changelist.html"
    readonly_fields = ["photo_preview"]
    inlines = [ProductImageInline]

    fieldsets = (
        (None, {'fields': ('name', 'brand', 'width', 'profile', 'diameter', 'seasonality', 'description')}),
        ('Ціни та наявність', {'fields': ('cost_price', 'stock_quantity')}),
        ('Головне фото', {'fields': ('photo', 'photo_url', 'photo_preview')}),
        ('Характеристики', {'fields': ('country', 'year', 'load_index', 'speed_index', 'stud_type', 'vehicle_type')}),
    )

    def price_display(self, obj): return obj.price
    price_display.short_description = "Ціна (+30%)"

    def photo_preview(self, obj):
        if obj.photo_url: return format_html('<img src="{}" style="max-height: 50px;"/>', obj.photo_url)
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
                # 1. Відкриваємо файл (Read only)
                wb = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
                sheet = wb.active
                
                created_count = 0
                updated_count = 0
                
                # Кеш брендів для швидкості
                existing_brands = {b.name.upper(): b for b in Brand.objects.all()}

                rows_iter = sheet.iter_rows(values_only=True)
                
                try:
                    header_row = next(rows_iter)
                except StopIteration:
                    messages.error(request, "Файл порожній.")
                    return redirect("..")

                # Функція пошуку колонки
                def find_col(aliases):
                    for idx, cell in enumerate(header_row):
                        val = str(cell or "").strip().lower()
                        for alias in aliases:
                            if val.startswith(alias): return idx
                    return None

                # Визначаємо індекси
                c_brand = find_col(["бренд", "brand", "фірма"]) or 0
                c_model = find_col(["модель", "model", "назва"]) or 1
                c_size = find_col(["типоразмер", "размер", "size"]) or 2
                c_season = find_col(["сезон", "season"]) or 3
                c_price = find_col(["цена", "price", "варт"]) or 4
                c_qty = find_col(["кол", "кільк", "qty"]) or 5
                c_country = find_col(["країна", "страна", "country"]) or 6
                c_year = find_col(["рік", "год", "year"]) or 7
                c_photo = find_col(["фото", "photo", "image"])
                
                # Проходимо по рядках (БЕЗ ТРАНЗАКЦІЇ!)
                for i, row in enumerate(rows_iter):
                    # Чистимо пам'ять кожні 100 рядків
                    if i % 100 == 0:
                        gc.collect()

                    if not row[c_brand] and not row[c_model]: continue

                    # Бренд
                    brand_name = str(row[c_brand]).strip()
                    if not brand_name or brand_name == "None": brand_name = "Unknown"
                    
                    brand_key = brand_name.upper()
                    if brand_key in existing_brands:
                        brand_obj = existing_brands[brand_key]
                    else:
                        brand_obj = Brand.objects.create(name=brand_name)
                        existing_brands[brand_key] = brand_obj # Додаємо в кеш

                    model_name = str(row[c_model]).strip()
                    
                    # Розмір
                    size_raw = str(row[c_size]).strip()
                    match = re.search(r'(\d+)/(\d+)\s*[a-zA-Z]*\s*(\d+)', size_raw)
                    if match:
                        w, p, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    else:
                        w, p, d = 0, 0, 0

                    # Унікальна назва
                    unique_name = model_name
                    if (w == 0 or p == 0 or d == 0) and size_raw:
                        unique_name = f"{model_name} [{size_raw}]"

                    # Сезон
                    season_raw = str(row[c_season]).lower() if row[c_season] else ""
                    season_key = 'all-season'
                    if 'зим' in season_raw or 'winter' in season_raw: season_key = 'winter'
                    elif 'літ' in season_raw or 'summer' in season_raw: season_key = 'summer'

                    # Ціна
                    try:
                        raw_price = row[c_price]
                        if isinstance(raw_price, (int, float)):
                            cost = float(raw_price)
                        else:
                            clean_price = re.sub(r'[^\d,.]', '', str(raw_price))
                            clean_price = clean_price.replace(',', '.')
                            if clean_price.count('.') > 1:
                                parts = clean_price.split('.')
                                clean_price = "".join(parts[:-1]) + "." + parts[-1]
                            cost = float(clean_price)
                    except: cost = 0.0

                    # Кількість
                    try:
                        qty_val = str(row[c_qty]).strip()
                        if '>' in qty_val: qty = 20
                        else: qty = int(re.sub(r'[^0-9]', '', qty_val) or 0)
                    except: qty = 0

                    # Дод. поля
                    country = str(row[c_country]).strip() if c_country and row[c_country] else "-"
                    try: year = int(row[c_year]) if c_year and row[c_year] else 2024
                    except: year = 2024
                    
                    photo_link = str(row[c_photo]).strip() if c_photo and row[c_photo] else None

                    # Запис (Одразу в базу!)
                    obj, created = Product.objects.update_or_create(
                        name=unique_name,
                        brand=brand_obj,
                        width=w, profile=p, diameter=d,
                        defaults={
                            'seasonality': season_key,
                            'cost_price': cost,
                            'stock_quantity': qty,
                            'country': country,
                            'year': year,
                            'description': f"Шини {brand_name} {model_name}. {size_raw}. {season_raw}."
                        }
                    )
                    
                    if photo_link and not obj.photo_url:
                        obj.photo_url = photo_link
                        obj.save(update_fields=['photo_url'])

                    if created: created_count += 1
                    else: updated_count += 1

                messages.success(request, f"Готово! ✅ Нових: {created_count}, 🔄 Оновлено: {updated_count}")

            except Exception as e:
                messages.error(request, f"Помилка: {e}")
            
            return redirect("..")

        form = ExcelImportForm()
        return render(request, "store/admin_import.html", {"form": form})

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(SiteBanner)
class SiteBannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_active']
