from django.contrib import admin
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
    # 'list_display' - це СПИСОК. Він у нас був правильний.
    list_display = ('name', 'brand', 'stock_quantity', 'seasonality', 'cost_price', 'price')
    list_filter = ('seasonality', 'brand') 
    search_fields = ('name', 'brand__name', 'width', 'profile', 'diameter')
    
    # --- ОСЬ ВИРІШЕННЯ: ---
    # 'fieldsets' - це СТОРІНКА РЕДАГУВАННЯ.
    # Ми групуємо всі наші поля для зручності.
    fieldsets = (
        (None, { # Головна інформація
            'fields': ('name', 'brand', 'seasonality')
        }),
        ('Розмір', { # Група "Розмір"
            'fields': ('width', 'profile', 'diameter')
        }),
        ('Ціна та Наявність', { # Група "Ціна та Наявність"
            'fields': ('cost_price', 'stock_quantity') # <--- ОСЬ ВАШЕ ПОЛЕ!
        }),
        ('Фото (Посилання)', { # Група "Фото"
            'fields': ('photo_url',)
        }),
    )

# --- Налаштування для Брендів (без змін) ---
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Реєструємо всі моделі
admin.site.register(Brand, BrandAdmin) 
admin.site.register(Product, ProductAdmin)
admin.site.register(Order, OrderAdmin)
