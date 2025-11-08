from django.contrib import admin
# ІМПОРТУЄМО "КРАН"
from import_export.admin import ImportExportModelAdmin
from .models import Brand, Product, Order, OrderItem
# ІМПОРТУЄМО "ІНСТРУКЦІЮ"
from .resources import ProductResource 

# --- Налаштування для Позицій в Замовленні (без змін) ---
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ('product', 'price_at_purchase', 'quantity')
    extra = 0 

# --- Налаштування для Замовлень (без змін) ---
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'phone', 'status', 'shipping_type', 'created_at')
    list_filter = ('status', 'shipping_type')
    search_fields = ('id', 'full_name', 'phone', 'email')
    list_editable = ('status',) 
    inlines = [OrderItemInline]

# --- ОНОВЛЕНІ Налаштування для Товарів (Шин) ---
# Ми міняємо 'admin.ModelAdmin' на 'ImportExportModelAdmin'
class ProductAdmin(ImportExportModelAdmin):
    # Кажемо, яку "інструкцію" використовувати
    resource_class = ProductResource 
    
    list_display = ('name', 'brand', 'stock_quantity', 'seasonality', 'cost_price', 'price')
    list_filter = ('seasonality', 'brand') 
    search_fields = ('name', 'brand__name', 'width', 'profile', 'diameter')
    
    fieldsets = (
        (None, {'fields': ('name', 'brand', 'seasonality')}),
        ('Розмір', {'fields': ('width', 'profile', 'diameter')}),
        ('Ціна та Наявність', {'fields': ('cost_price', 'stock_quantity')}),
        ('Фото (Посилання)', {'fields': ('photo_url',)}),
    )

# --- Налаштування для Брендів (без змін) ---
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Реєструємо всі моделі
admin.site.register(Brand, BrandAdmin) 
admin.site.register(Product, ProductAdmin)
admin.site.register(Order, OrderAdmin)
