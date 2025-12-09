from django.db import models
from django.contrib.auth.models import User
import decimal

# --- 0. НАЛАШТУВАННЯ САЙТУ ---
class SiteSettings(models.Model):
    global_markup = models.DecimalField(max_digits=5, decimal_places=2, default=1.30, verbose_name="Глобальна націнка")

    class Meta: verbose_name = "Налаштування Сайту"
    
    def __str__(self): return f"Націнка: {self.global_markup}"

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(id=1)
        return obj

# --- 1. БРЕНД ---
class Brand(models.Model):
    CATEGORY_CHOICES = [
        ('budget', '💸 Економ / Таксі'),
        ('medium', '⚖️ Ціна / Якість'),
        ('top', '💎 Топ Бренд'),
    ]
    name = models.CharField(max_length=100, unique=True, verbose_name="Назва бренду")
    country = models.CharField(max_length=100, blank=True, null=True, verbose_name="Країна")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='budget', verbose_name="Категорія (для Бота)")

    def __str__(self): return self.name

# --- 2. ТОВАР ---
class Product(models.Model):
    SEASON_CHOICES = [('winter', 'Зимові'), ('summer', 'Літні'), ('all-season', 'Всесезонні')]
    
    name = models.CharField(max_length=255, verbose_name="Назва")
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, verbose_name="Бренд")
    width = models.IntegerField(default=0, verbose_name="Ширина")
    profile = models.IntegerField(default=0, verbose_name="Профіль")
    diameter = models.IntegerField(default=0, verbose_name="Діаметр")
    seasonality = models.CharField(max_length=20, choices=SEASON_CHOICES, default='all-season')
    
    description = models.TextField(blank=True, verbose_name="Опис")
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Закупка")
    stock_quantity = models.IntegerField(default=0, verbose_name="Наявність")
    discount_percent = models.IntegerField(default=0, verbose_name="Знижка (%)")
    
    photo = models.ImageField(upload_to='products/', blank=True, null=True)
    photo_url = models.URLField(max_length=1024, blank=True, null=True)

    # Характеристики
    country = models.CharField(max_length=50, blank=True, null=True)
    year = models.IntegerField(default=2024)
    load_index = models.CharField(max_length=50, blank=True, null=True)
    speed_index = models.CharField(max_length=50, blank=True, null=True)
    stud_type = models.CharField(max_length=50, default="Не шип")
    vehicle_type = models.CharField(max_length=50, default="Легковий")

    @property
    def old_price(self):
        try: markup = SiteSettings.get_solo().global_markup
        except: markup = decimal.Decimal('1.30')
        return (self.cost_price * markup).quantize(decimal.Decimal('0.01'))

    @property
    def price(self):
        base = self.old_price
        if self.discount_percent > 0:
            factor = decimal.Decimal(100 - self.discount_percent) / 100
            return (base * factor).quantize(decimal.Decimal('0.01'))
        return base

    def __str__(self): return f"{self.name} ({self.width}/{self.profile} R{self.diameter})"

# --- 3. ЗАМОВЛЕННЯ ---
class Order(models.Model):
    STATUS_CHOICES = [('new', 'Нове'), ('processing', 'В обробці'), ('shipped', 'Відправлено'), ('completed', 'Завершено'), ('canceled', 'Скасовано')]
    SHIPPING_CHOICES = [('pickup', 'Самовивіз'), ('nova_poshta', 'Нова Пошта')]
    
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    shipping_type = models.CharField(max_length=20, choices=SHIPPING_CHOICES, default='pickup')
    full_name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    nova_poshta_branch = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self): return f"Order #{self.id}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)
    
    # 🔥 ОСЬ ЦЕЙ МЕТОД Я ПОВЕРНУВ, ЩОБ АДМІНКА НЕ ПАДАЛА 🔥
    def get_cost(self):
        return self.price_at_purchase * self.quantity

    def __str__(self): return f"{self.quantity} x {self.product}"

# --- 4. ІНШЕ ---
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_gallery/', blank=True, null=True)
    image_url = models.URLField(max_length=1024, blank=True, null=True)

class SiteBanner(models.Model):
    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to='banners/', blank=True, null=True)
    image_url = models.URLField(max_length=1024, blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class AboutImage(models.Model):
    image = models.ImageField(upload_to='about_us/')
    image_url = models.URLField(max_length=1024, blank=True, null=True)
    description = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
