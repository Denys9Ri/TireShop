from django.db import models
from django.contrib.auth.models import User
import decimal

# --- 0. НАЛАШТУВАННЯ САЙТУ (Глобальна націнка) ---
class SiteSettings(models.Model):
    # Націнка, наприклад 1.30 (це 30%)
    global_markup = models.DecimalField(max_digits=5, decimal_places=2, default=1.30, verbose_name="Глобальна націнка (коефіцієнт)")

    class Meta:
        verbose_name = "Налаштування Сайту (Націнка)"
        verbose_name_plural = "Налаштування Сайту (Націнка)"

    def __str__(self):
        return f"Поточна націнка: {self.global_markup}"

    # Метод, щоб завжди брати єдиний запис налаштувань
    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(id=1)
        return obj

# --- 1. БРЕНД ---
class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Назва бренду")
    def __str__(self):
        return self.name

# --- 2. ТОВАР (ШИНА) ---
class Product(models.Model):
    SEASON_CHOICES = [('winter', 'Зимові'), ('summer', 'Літні'), ('all-season', 'Всесезонні')]
    
    name = models.CharField(max_length=255, verbose_name="Назва шини (модель)")
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, verbose_name="Бренд")
    
    width = models.IntegerField(default=0, verbose_name="Ширина (напр. 205)")
    profile = models.IntegerField(default=0, verbose_name="Профіль (напр. 55)")
    diameter = models.IntegerField(default=0, verbose_name="Діаметр (напр. 16)")
    seasonality = models.CharField(max_length=20, choices=SEASON_CHOICES, default='all-season')
    
    description = models.TextField(blank=True, verbose_name="Опис")
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ціна з прайсу (закупка)")
    stock_quantity = models.IntegerField(default=0, verbose_name="Наявність (на складі)")
    
    # ЗНИЖКА (НОВЕ ПОЛЕ)
    discount_percent = models.IntegerField(default=0, verbose_name="Знижка (%)")
    
    photo = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Фото (застаріле)")
    photo_url = models.URLField(max_length=1024, blank=True, null=True, verbose_name="Головне URL Фото (Обкладинка)")

    # ХАРАКТЕРИСТИКИ
    country = models.CharField(max_length=50, blank=True, null=True, verbose_name="Країна виробник")
    year = models.IntegerField(default=2024, verbose_name="Рік виробництва")
    load_index = models.CharField(max_length=50, blank=True, null=True, verbose_name="Індекс навантаження")
    speed_index = models.CharField(max_length=50, blank=True, null=True, verbose_name="Індекс швидкості")
    stud_type = models.CharField(max_length=50, default="Не шип", verbose_name="Шипи")
    vehicle_type = models.CharField(max_length=50, default="Легковий", verbose_name="Тип авто")

    # --- 1. СТАРА ЦІНА (Ціна продажу ДО знижки) ---
    @property
    def old_price(self):
        # Беремо глобальну націнку з адмінки
        try:
            settings = SiteSettings.get_solo()
            markup = settings.global_markup
        except:
            markup = decimal.Decimal('1.30') # Про всяк випадок, якщо бази ще немає
            
        base_price = self.cost_price * markup
        return base_price.quantize(decimal.Decimal('0.01'))

    # --- 2. АКТУАЛЬНА ЦІНА (З урахуванням знижки) ---
    @property
    def price(self):
        base = self.old_price
        if self.discount_percent > 0:
            # Віднімаємо відсоток
            discount_factor = decimal.Decimal(100 - self.discount_percent) / 100
            final_price = base * discount_factor
            return final_price.quantize(decimal.Decimal('0.01'))
        return base

    def __str__(self):
        if self.brand:
            return f"{self.brand.name} {self.name} ({self.width}/{self.profile} R{self.diameter})"
        return f"{self.name} ({self.width}/{self.profile} R{self.diameter})"

# --- 3. ЗАМОВЛЕННЯ ---
class Order(models.Model):
    STATUS_CHOICES = [('new', 'Нове замовлення'), ('processing', 'В обробці'), ('shipped', 'Відправлено'), ('completed', 'Завершено'), ('canceled', 'Скасовано')]
    SHIPPING_CHOICES = [('pickup', 'Самовивіз'), ('nova_poshta', 'Нова Пошта')]
    
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Клієнт")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата створення")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Статус")
    shipping_type = models.CharField(max_length=20, choices=SHIPPING_CHOICES, default='pickup', verbose_name="Тип доставки")
    full_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="ПІБ отримувача")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Телефон")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Місто/Село")
    nova_poshta_branch = models.CharField(max_length=100, blank=True, null=True, verbose_name="Відділення НП")
    
    def __str__(self):
        return f"Замовлення #{self.id} від {self.created_at.strftime('%Y-%m-%d')}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name="Замовлення")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, verbose_name="Товар")
    quantity = models.IntegerField(default=1, verbose_name="Кількість")
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ціна (на момент покупки)")
    
    def get_cost(self):
        return self.price_at_purchase * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name if self.product else 'Видалений товар'}"

# --- 4. ДОДАТКОВІ ФОТО ---
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', verbose_name="Товар")
    image = models.ImageField(upload_to='product_gallery/', blank=True, null=True, verbose_name="Фото файлом")
    image_url = models.URLField(max_length=1024, blank=True, null=True, verbose_name="Посилання на фото (для Render)")
    
    def __str__(self):
        return f"Фото для {self.product.name}"

# --- 5. БАНЕР ---
class SiteBanner(models.Model):
    title = models.CharField(max_length=100, verbose_name="Назва (для себе)")
    image = models.ImageField(upload_to='banners/', blank=True, null=True, verbose_name="Фото файлом")
    image_url = models.URLField(max_length=1024, blank=True, null=True, verbose_name="Посилання на фото (для Render)")
    link = models.URLField(blank=True, null=True, verbose_name="Посилання при кліку (куди веде)")
    is_active = models.BooleanField(default=True, verbose_name="Активний")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# --- 6. ФОТО ДЛЯ СТОРІНКИ "ПРО НАС" ---
class AboutImage(models.Model):
    image = models.ImageField(upload_to='about_us/', verbose_name="Фото складу/офісу")
    image_url = models.URLField(max_length=1024, blank=True, null=True, verbose_name="Посилання на фото (для Render)")
    description = models.CharField(max_length=200, blank=True, verbose_name="Підпис (не обов'язково)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Фото 'Про нас'"
        verbose_name_plural = "Фото 'Про нас' (Склад)"

    def __str__(self):
        return f"Фото {self.id}"
