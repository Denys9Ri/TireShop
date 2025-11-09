from django.contrib import admin
# Ми ВИДАЛИЛИ 'ImportExportModelAdmin'
from .models import Brand, Product, Order, OrderItem, ProductImage
# Ми ВИДАЛИЛИ '.resources' 

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
# Ми повернули 'admin.ModelAdmin'
class ProductAdmin(admin.ModelAdmin):
    # Ми ВИДАЛИЛИ 'resource_class'
    list_display = ('name', 'brand', 'stock_quantity', 'cost_price', 'price', 'photo_url') 
    list_filter = ('seasonality', 'brand') 
    search_fields = ('name', 'brand__name')
    list_editable = ('stock_quantity', 'cost_price', 'photo_url')
    list_per_page = 50 
    
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
