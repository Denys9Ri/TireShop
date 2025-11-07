from django.contrib import admin
# Ми додали 'Brand' до списку імпорту
from .models import Brand, Product, Order, OrderItem

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
class ProductAdmin(admin.ModelAdmin):
    # 'price' - це націнка. 
    # Ми замінили 'size' на нові поля
    list_display = ('name', 'brand', 'width', 'profile', 'diameter', 'seasonality', 'cost_price', 'price')
    list_filter = ('seasonality', 'brand') # Додали фільтр за брендом
    # Додали пошук за новими полями
    search_fields = ('name', 'brand__name', 'width', 'profile', 'diameter')

# --- НОВИЙ клас для адмінки Брендів ---
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Реєструємо всі моделі
admin.site.register(Brand, BrandAdmin) # Додали Бренд
admin.site.register(Product, ProductAdmin)
admin.site.register(Order, OrderAdmin)
