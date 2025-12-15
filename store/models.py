from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
import decimal

# --- 0. НАЛАШТУВАННЯ ---
class SiteSettings(models.Model):
    # Змінив default=1.30 на default='1.30' (рядок), щоб уникнути float
    global_markup = models.DecimalField(max_digits=5, decimal_places=2, default='1.30', verbose_name="Націнка")

    class Meta: verbose_name = "Налаштування"
    def __str__(self): return f"Націнка: {self.global_markup}"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj

# --- 1. БРЕНД ---
class Brand(models.Model):
    CATEGORY_CHOICES = [('budget', '💸 Економ'), ('medium', '⚖️ Ціна/Якість'), ('top', '💎 Топ')]
    name = models.CharField(max_length=100, unique=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='budget')
    def __str__(self): return self.name

# --- 2. ТОВАР ---
class Product(models.Model):
    SEASON_CHOICES = [('winter', 'Зимові'), ('summer', 'Літні'), ('all-season', 'Всесезонні')]
    
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True, verbose_name="URL-адреса")
    
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True)
    width = models.IntegerField(default=0)
    profile = models.IntegerField(default=0)
    diameter = models.IntegerField(default=0)
    seasonality = models.CharField(max_length=20, choices=SEASON_CHOICES, default='all-season')

    # --- SEO ПОЛЯ (Нові) ---
    seo_title = models.CharField(max_length=500, blank=True, null=True, verbose_name="SEO Title (Google)")
    seo_h1 = models.CharField(max_length=255, blank=True, null=True, verbose_name="SEO H1 (Заголовок)")
    seo_text = models.TextField(blank=True, null=True, verbose_name="SEO Текст")
    
    description = models.TextField(blank=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_quantity = models.IntegerField(default=0)
    discount_percent = models.IntegerField(default=0)
    
    photo_url = models.URLField(max_length=1024, blank=True, null=True)
    photo = models.ImageField(upload_to='products/', blank=True, null=True)

    # Технічні характеристики
    country = models.CharField(max_length=50, blank=True, null=True)
    year = models.IntegerField(default=2024)
    load_index = models.CharField(max_length=10, blank=True, null=True, verbose_name="Індекс навантаження")
    speed_index = models.CharField(max_length=10, blank=True, null=True, verbose_name="Індекс швидкості")
    stud_type = models.CharField(max_length=50, default="Не шип")
    vehicle_type = models.CharField(max_length=50, default="Легковий")

    # Авто-генерація SLUG
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = f"{self.brand.name if self.brand else ''}-{self.name}-{self.width}-{self.profile}-{self.diameter}"
            self.slug = slugify(base_slug)[:250]
        super().save(*args, **kwargs)

    # 🔥 ВИПРАВЛЕНА ЛОГІКА ЦІНИ (Decimal only) 🔥
    @property
    def old_price(self):
        try:
            settings = SiteSettings.get_solo()
            markup = settings.global_markup
            # Гарантуємо, що markup це Decimal
            if not isinstance(markup, decimal.Decimal):
                markup = decimal.Decimal(str(markup))
        except:
            markup = decimal.Decimal('1.30')
            
        # Гарантуємо, що cost_price це Decimal
        cost = self.cost_price
        if not isinstance(cost, decimal.Decimal):
            cost = decimal.Decimal(str(cost))
            
        final_old = cost * markup
        return final_old.quantize(decimal.Decimal('0.01'))

    @property
    def price(self):
        base = self.old_price # Це вже Decimal (див. вище)
        
        if self.discount_percent > 0:
            # Формула: base * ((100 - discount) / 100)
            # Все переводимо в Decimal перед математикою
            d_100 = decimal.Decimal('100')
            d_percent = decimal.Decimal(self.discount_percent)
            
            factor = (d_100 - d_percent) / d_100
            new_price = base * factor
            return new_price.quantize(decimal.Decimal('0.01'))
            
        return base

    def __str__(self): return self.slug

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
    def get_cost(self): return self.price_at_purchase * self.quantity
    def __str__(self): return f"{self.quantity} x {self.product}"

# --- 4. ДОДАТКОВІ ---
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_gallery/', blank=True, null=True)
    image_url = models.URLField(max_length=1024, blank=True, null=True)

class SiteBanner(models.Model):
    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to='banners/', blank=True, null=True, verbose_name="Фото (Файл)")
    image_url = models.URLField(max_length=1024, blank=True, null=True, verbose_name="Фото (Посилання)")
    link = models.URLField(blank=True, null=True, verbose_name="Куди вести при кліку")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self): return self.title

class AboutImage(models.Model):
    image = models.ImageField(upload_to='about_us/')
    image_url = models.URLField(max_length=1024, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
