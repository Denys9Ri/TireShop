from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django import forms
from django.http import HttpResponse, FileResponse
from django.utils.html import format_html
from django.template.loader import render_to_string
from django.db.models import Q 
import openpyxl
import re
import gc
import io
from xhtml2pdf import pisa # 🎉 Бібліотека для PDF

from .models import Product, Brand, Order, OrderItem, ProductImage, SiteSettings, AboutImage

# ==========================================
# 🔥 ЛОГІКА ГЕНЕРАЦІЇ PDF-ЧЕКА 🔥
# ==========================================
def generate_order_pdf(order):
    """
    Бере об'єкт замовлення, рендерить HTML-шаблон і конвертує його в PDF.
    Повертає готовий байтовий потік (файл в пам'яті).
    """
    total_cost = sum(item.get_cost() for item in order.items.all())
    
    # Дані, які ми передаємо в HTML-шаблон
    context = {
        'order': order,
        'total_cost': total_cost,
    }
    
    # 1. Перетворюємо Django-шаблон в готовий HTML-код (рядок)
    html_string = render_to_string('store/pdf/invoice.html', context)
    
    # 2. Створюємо буфер в пам'яті, куди запишемо PDF
    result = io.BytesIO()
    
    # 3. Магія: конвертуємо HTML в PDF
    # encoding='UTF-8' критично для підтримки української мови!
    pisa_status = pisa.CreatePDF(io.BytesIO(html_string.encode("UTF-8")), dest=result, encoding='UTF-8')
    
    # Якщо виникла помилка при генерації
    if pisa_status.err:
        return None
        
    # Повертаємо потік з початку
    result.seek(0)
    return result

# --- ЗАМОВЛЕННЯ ---
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0
    # У inline замовлення не показуємо собівартість, тільки ціну продажу
    fields = ['product', 'quantity', 'price_at_purchase', 'get_cost_display']
    readonly_fields = ['get_cost_display']
    
    def get_cost_display(self, obj):
        return f"{obj.get_cost():.2f} грн"
    get_cost_display.short_description = "Сума"

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Додали 'print_invoice_button' в список колонок
    list_display = ['id', 'status', 'created_at', 'full_name', 'phone', 'shipping_type', 'order_items_summary', 'total_cost', 'print_invoice_button']
    list_filter = ['status', 'created_at', 'shipping_type']
    search_fields = ['id', 'full_name', 'phone', 'email']
    inlines = [OrderItemInline]
    list_editable = ['status']
    readonly_fields = ['created_at', 'total_cost_detailed']
    
    # Групування полів всередині замовлення
    fieldsets = (
        ('Статус та Доставка', {'fields': ('status', 'shipping_type', 'created_at')}),
        ('Дані Клієнта', {'fields': ('full_name', 'phone', 'email')}),
        ('Адреса (для НП)', {'fields': ('city', 'nova_poshta_branch')}),
        ('Фінанси', {'fields': ('total_cost_detailed',)}),
    )

    # 1. Загальна сума в списку
    def total_cost(self, obj):
        sum_val = sum(item.get_cost() for item in obj.items.all())
        return format_html("<b>{} грн</b>", f"{sum_val:.2f}")
    total_cost.short_description = 'Сума'

    # 2. Детальна сума всередині картки
    def total_cost_detailed(self, obj):
        sum_val = sum(item.get_cost() for item in obj.items.all())
        return f"{sum_val:.2f} грн"
    total_cost_detailed.short_description = 'Разом до сплати'

    # 3. Колонка "Що замовили"
    def order_items_summary(self, obj):
        items = obj.items.all()
        result = []
        for item in items:
            name = item.product.display_name if item.product else "Товар видалено"
            result.append(f"{name} x{item.quantity}")
        return ", ".join(result)
    order_items_summary.short_description = 'Товари'

    # 🔥 4. СТВОРЕННЯ КНОПКИ ДРУКУ В ТАБЛИЦІ 🔥
    def print_invoice_button(self, obj):
        """Створює красиву синю кнопку посилання на генерацію PDF"""
        return format_html(
            '<a class="button" href="{}/print/" target="_blank" style="background-color: #0d6efd; padding: 5px 10px; border-radius: 4px; color: white;">📄 Чек</a>',
            obj.id
        )
    print_invoice_button.short_description = 'Друк'

    # 🔥 5. ПІДКЛЮЧЕННЯ URL ДЛЯ ДРУКУ 🔥
    def get_urls(self):
        """Додає новий шлях замовлення/ID/print/"""
        urls = super().get_urls()
        my_urls = [
            # Шлях для друку конкретного замовлення
            path('<int:order_id>/print/', self.admin_print_invoice, name="order_print_invoice"),
        ]
        return my_urls + urls

    # 🔥 6. VIEW-ФУНКЦІЯ ДЛЯ ДРУКУ (ОБРОБКА КЛІКУ) 🔥
    def admin_print_invoice(self, request, order_id):
        """Отримує ID, генерує PDF і повертає його як файл завантаження"""
        order = get_object_or_404(Order, id=order_id)
        
        # Запускаємо нашу логіку генерації
        pdf_file = generate_order_pdf(order)
        
        if pdf_file:
            # Створюємо ім'я файлу: check_R16_105.pdf
            filename = f"check_R16_{order.id}.pdf"
            
            # Повертаємо файл клієнту
            # as_attachment=True - змусить браузер завантажити файл, False - відкриє в новій вкладці
            return FileResponse(pdf_file, as_attachment=False, content_type='application/pdf', filename=filename)
        else:
            messages.error(request, f"Помилка генерації PDF для замовлення #{order_id}")
            return redirect("..")

# --- ГАЛЕРЕЯ ТОВАРУ ---
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image_url', 'image', 'preview')
    readonly_fields = ('preview',)
    def preview(self, obj):
        if obj.image_url: return format_html('<img src="{}" style="height: 50px; border-radius: 4px;"/>', obj.image_url)
        if obj.image: return format_html('<img src="{}" style="height: 50px; border-radius: 4px;"/>', obj.image.url)
        return "-"

# --- НАЛАШТУВАННЯ САЙТУ ---
@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ['global_markup']
    def has_add_permission(self, request): return not SiteSettings.objects.exists()

# --- ФОРМИ ІМПОРТУ ---
class ExcelImportForm(forms.Form):
    excel_file = forms.FileField(label="Прайс-лист (Товари)")
    start_row = forms.IntegerField(initial=2, min_value=2, label="Почати з рядка")
    end_row = forms.IntegerField(initial=2000, min_value=2, label="Закінчити рядком")
class PhotoImportForm(forms.Form):
    excel_file = forms.FileField(label="Файл з ФОТО (Brand, Model, URL)")
class SeoImportForm(forms.Form):
    excel_file = forms.FileField(label="SEO Файл (.xlsx)")
    start_row = forms.IntegerField(initial=2, min_value=2, label="Почати з рядка")
    end_row = forms.IntegerField(initial=500, min_value=2, label="Закінчити рядком")

# --- ТОВАР ---
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'width', 'profile', 'diameter', 'price_display', 'discount_percent', 'stock_quantity', 'photo_preview']
    list_filter = ['brand', 'seasonality', 'diameter', 'stud_type']
    search_fields = ['name', 'width', 'brand__name', 'slug']
    change_list_template = "store/admin_changelist.html"
    readonly_fields = ["photo_preview", "final_price_preview"]
    inlines = [ProductImageInline]
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'brand', 'width', 'profile', 'diameter', 'seasonality', 'description')}),
        ('SEO', {'fields': ('seo_title', 'seo_h1', 'seo_text')}), 
        ('Фінанси', {'fields': ('cost_price', 'discount_percent', 'final_price_preview', 'stock_quantity')}),
        ('Фото', {'fields': ('photo', 'photo_url', 'photo_preview')}),
        ('Хар-ки', {'fields': ('country', 'year', 'load_index', 'speed_index', 'stud_type', 'vehicle_type')}),
    )
    def price_display(self, obj): return f"{obj.price} грн"
    price_display.short_description = "Ціна"
    def final_price_preview(self, obj): return f"{obj.price} грн"
    def photo_preview(self, obj):
        if obj.photo_url: return format_html('<img src="{}" style="max-height: 50px;"/>', obj.photo_url)
        return "—"
    photo_preview.short_description = "Фото"
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-excel/', self.import_excel, name="import_excel"),
            path('import-photos/', self.import_photos, name="import_photos"),
            path('import-seo/', self.import_seo, name="import_seo"),
            path('export-models/', self.export_unique_models, name="export_unique_models"),
        ]
        return my_urls + urls
    # (Логіку імпорту Excel я пропускаю, вона залишається незмінною у твоєму файлі)
    def export_unique_models(self, request): pass
    def import_photos(self, request): pass
    def import_excel(self, request): pass
    def import_seo(self, request): pass

# --- БРЕНД ---
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'country'] 
    list_editable = ['category'] 
    list_filter = ['category']
    search_fields = ['name']

# --- ФОТОГАЛЕРЕЯ СКЛАДУ ---
@admin.register(AboutImage)
class AboutImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at', 'image_preview']
    ordering = ['-created_at']
    def image_preview(self, obj):
        if obj.image: return format_html('<img src="{}" style="height: 100px; border-radius: 4px;"/>', obj.image.url)
        return "-"
    image_preview.short_description = "Попередній перегляд"
