from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
# --- ДОДАЄМО 'ProductImage' ---
from .models import Brand, Product, Order, OrderItem, ProductImage
from .resources import ProductResource 

# --- (Код OrderItemInline та OrderAdmin без змін) ---
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ('product', 'price_at_purchase', 'quantity')
    extra = 0 

class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'phone', 'status', 'shipping_type', 'created_at')
    list_filter = ('status', 'shipping_type')
    search_fields = ('id', 'full_name', 'phone', 'email')
    list_editable = ('status',) 
    inlines = [OrderItemInline]

# --- НОВИЙ КЛАС ДЛЯ "ФОТОАЛЬБОМУ" ---
# Це каже "Показуй фотоальбом як рядки"
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    # Даємо 3 порожніх слоти для додавання посилань
    extra = 3 
    # Вказуємо, що поле одне
    fields = ('image_url',) 

# --- ОНОВЛЕНІ Налаштування для Товарів (Шин) ---
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource 
    list_display = ('name', 'brand', 'stock_quantity', 'seasonality', 'cost_price', 'price')
    list_filter = ('seasonality', 'brand') 
    search_fields = ('name', 'brand__name', 'width', 'profile', 'diameter')
    
    fieldsets = (
        (None, {'fields': ('name', 'brand', 'seasonality')}),
        ('Розмір', {'fields': ('width', 'profile', 'diameter')}),
        ('Ціна та Наявність', {'fields': ('cost_price', 'stock_quantity')}),
        ('Головне Фото (Обкладинка)', { 
            'fields': ('photo_url',)
        }),
    )
    
    # --- ДОДАЄМО "ФОТОАЛЬБОМ" СЮДИ ---
    # Це додасть секцію "+ Add another Product Image"
    inlines = [ProductImageInline]

# --- Налаштування для Брендів (без змін) ---
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# --- РЕЄСТРУЄМО ВСЕ (включаючи ProductImage) ---
admin.site.register(Brand, BrandAdmin) 
admin.site.register(Product, ProductAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(ProductImage) # Можна, але не обов'язково
