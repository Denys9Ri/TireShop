from django.contrib import admin
from .models import Product, Order, OrderItem

# --- Налаштування для показу Позицій в Замовленні ---
# Це дозволить нам бачити і редагувати товари 
# ПРЯМО всередині картки самого замовлення
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    # 'readonly_fields' не дасть адміну випадково змінити ціну покупки
    readonly_fields = ('product', 'price_at_purchase', 'quantity')
    extra = 0 # Не показувати зайвих порожніх слотів для додавання

# --- Налаштування для Замовлень ---
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'phone', 'status', 'shipping_type', 'created_at')
    list_filter = ('status', 'shipping_type') # Фільтри збоку
    search_fields = ('id', 'full_name', 'phone', 'email')
    
    # Дозволяє редагувати статус прямо зі списку замовлень
    list_editable = ('status',) 
    
    # Включаємо Позиції в картку Замовлення
    inlines = [OrderItemInline]

# --- Налаштування для Товарів (Шин) ---
class ProductAdmin(admin.ModelAdmin):
    # 'price' - це ваша властивість з націнкою 30%
    list_display = ('name', 'size', 'seasonality', 'cost_price', 'price')
    list_filter = ('seasonality',)
    search_fields = ('name', 'size')

# Реєструємо наші моделі та їх налаштування в адмінці
admin.site.register(Product, ProductAdmin)
admin.site.register(Order, OrderAdmin)
