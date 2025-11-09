from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
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

# --- (Код ProductImageInline без змін) ---
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3 
    fields = ('image_url',) 

# --- ОНОВЛЕНІ Налаштування для Товарів (Шин) ---
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource 
    
    # 1. Додаємо 'photo_url' до списку видимих полів
    list_display = ('name', 'brand', 'stock_quantity', 'cost_price', 'price', 'photo_url') 
    
    list_filter = ('seasonality', 'brand') 
    search_fields = ('name', 'brand__name') # Пошук за назвою та брендом
    
    # --- ОСЬ ГОЛОВНЕ ВИРІШЕННЯ ---
    # 2. Кажемо, що ці 3 поля можна редагувати ПРЯМО У СПИСКУ
    list_editable = ('stock_quantity', 'cost_price', 'photo_url')
    
    # 3. Прискорюємо завантаження адмінки
    list_per_page = 50 
    
    # 'fieldsets' та 'inlines' (для сторінки деталей) залишаються без змін
    fieldsets = (
        (None, {'fields': ('name', 'brand', 'seasonality')}),
        ('Розмір', {'fields': ('width', 'profile', 'diameter')}),
        ('Ціна та Наявність', {'fields': ('cost_price', 'stock_quantity')}),
        ('Головне Фото (Обкладинка)', { 
            'fields': ('photo_url',)
        }),
    )
    inlines = [ProductImageInline]

# --- (Решта коду без змін) ---
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
admin.site.register(Brand, BrandAdmin) 
admin.site.register(Product, ProductAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(ProductImage)
