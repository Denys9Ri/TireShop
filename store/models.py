from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
import decimal
import re

# --- 0. НАЛАШТУВАННЯ ---
class SiteSettings(models.Model):
    global_markup = models.DecimalField(max_digits=5, decimal_places=2, default='1.30', verbose_name="Націнка")

    class Meta: 
        verbose_name = "Налаштування"
        verbose_name_plural = "Налаштування"

    def __str__(self): return f"Націнка: {self.global_markup}"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj

# --- 1. БРЕНД ---
class Brand(models.Model):
    CATEGORY_CHOICES = [('budget', '💸 Економ'), ('medium', '⚖️ Ціна/Якість'), ('top', '💎 Топ')]

    name = models.CharField(max_length=100, unique=True, verbose_name="Назва бренду")
    slug = models.SlugField(max_length=100, unique=True, null=True, blank=True, verbose_name="URL (Slug)")
    image = models.ImageField("Логотип", upload_to='brands/', blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True, verbose_name="Країна бренду")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='budget', verbose_name="Категорія")

    # 🔥 НОВІ ПОЛЯ ДЛЯ ЛЕНДІНГУ БРЕНДУ 🔥
    description = models.TextField(blank=True, verbose_name="Хто цей бренд (Опис)")
    target_audience = models.TextField(blank=True, verbose_name="Для кого підходить")
    pros = models.TextField(blank=True, verbose_name="Сильні сторони (Плюси)")
    cons = models.TextField(blank=True, verbose_name="Слабкі сторони (Мінуси)")
    
    # Для SEO сторінки бренду
    seo_title = models.CharField(max_length=255, blank=True, verbose_name="SEO Title")
    seo_h1 = models.CharField(max_length=255, blank=True, verbose_name="SEO H1")
    seo_text = models.TextField(blank=True, verbose_name="SEO Текст (знизу)")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:110]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Бренд"
        verbose_name_plural = "Бренди"


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

    # --- SEO ПОЛЯ ---
    seo_title = models.CharField(max_length=500, blank=True, null=True, verbose_name="SEO Title")
    seo_h1 = models.CharField(max_length=255, blank=True, null=True, verbose_name="SEO H1")
    seo_text = models.TextField(blank=True, null=True, verbose_name="SEO Текст")
    
    description = models.TextField(blank=True)
    
    # ЦІНИ
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Собівартість")
    price = models.DecimalField("Ціна продажу", max_digits=10, decimal_places=0, default=0)
    
    stock_quantity = models.IntegerField(default=0)
    discount_percent = models.IntegerField(default=0)
    
    photo_url = models.URLField(max_length=1024, blank=True, null=True)
    photo = models.ImageField(upload_to='products/', blank=True, null=True)

    @property
    def display_name(self):
        text = self.name
        text = text.replace("Шина", "").replace("шина", "")
        if self.brand:
            text = re.sub(f"^{self.brand.name}", "", text, flags=re.IGNORECASE)
            text = re.sub(f"\({self.brand.name}\)", "", text, flags=re.IGNORECASE)

        features = []
        if re.search(r'\bXL\b', text, re.IGNORECASE) or "EXTRA LOAD" in text.upper():
            features.append("XL")
            text = re.sub(r'\bXL\b', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\bEXTRA LOAD\b', '', text, flags=re.IGNORECASE)
            
        if re.search(r'\bRunFlat\b', text, re.IGNORECASE) or re.search(r'\bRFT\b', text, re.IGNORECASE):
            features.append("RunFlat")
            text = re.sub(r'\bRunFlat\b', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\bRFT\b', '', text, flags=re.IGNORECASE)

        index_match = re.search(r'\b\d{2,3}[A-Z]\b', text)
        index_val = ""
        if index_match:
            index_val = index_match.group(0)
            text = text.replace(index_val, "") 

        text = re.sub(r'\d{3}/\d{2}\s?[R|Z|r|z]\d{1,2}', '', text)
        model_name = text.strip()
        model_name = re.sub(r'^\W+|\W+$', '', model_name)
        model_name = re.sub(r'\s+', ' ', model_name).strip()

        size_clean = f"{self.width}/{self.profile} R{self.diameter}"
        
        final_parts = []
        if model_name: final_parts.append(model_name)
        if features: final_parts.extend(features)
        final_parts.append(size_clean)
        if index_val: final_parts.append(index_val)

        res = " ".join(final_parts)
        return res if len(res) > 5 else self.name
        
    country = models.CharField(max_length=50, blank=True, null=True)
    year = models.IntegerField(default=2024)
    load_index = models.CharField(max_length=10, blank=True, null=True)
    speed_index = models.CharField(max_length=10, blank=True, null=True)
    stud_type = models.CharField(max_length=50, default="Не шип")
    vehicle_type = models.CharField(max_length=50, default="Легковий")

    @property
    def old_price(self):
        if self.discount_percent > 0:
            return int(self.price * 100 / (100 - self.discount_percent))
        return None

    def save(self, *args, **kwargs):
        if not self.slug:
            slug_candidate = f"{self.brand.name}-{self.name}" if self.brand else self.name
            slug_candidate = slug_candidate.replace('/', '')
            self.slug = slugify(slug_candidate)

        original_slug = self.slug
        counter = 1
        while Product.objects.filter(slug=self.slug).exclude(id=self.id).exists():
            self.slug = f"{original_slug}-{counter}"
            counter += 1

        try:
            settings = SiteSettings.get_solo()
            markup = decimal.Decimal(str(settings.global_markup))
        except:
            markup = decimal.Decimal('1.30')
        
        cost = decimal.Decimal(str(self.cost_price))
        base_price = cost * markup
        
        if self.discount_percent > 0:
            factor = (decimal.Decimal('100') - decimal.Decimal(self.discount_percent)) / decimal.Decimal('100')
            final_price = base_price * factor
        else:
            final_price = base_price
            
        self.price = int(final_price)
        super().save(*args, **kwargs)

    def __str__(self): return self.slug

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товари"

# --- 3. ЗАМОВЛЕННЯ (🔥 ОНОВЛЕНА ВОРОНКА СТАТУСІВ 🔥) ---
class Order(models.Model):
    STATUS_CHOICES = [
        ('new', '🔴 Нове'),
        ('confirmed', '🟡 Підтверджено'),
        ('waiting_supplier', '⏳ Чекаємо від постачальника'),
        ('pickup_vk3', '🏢 Самовивіз ВК3'),
        ('waiting_payment', '💳 Очікує оплати / Передоплати'),
        ('shipped', '🚚 Передано в доставку (НП)'),
        ('completed', '✅ Успішно завершено'),
        ('canceled', '❌ Скасовано')
    ]
    SHIPPING_CHOICES = [('pickup', 'Самовивіз'), ('nova_poshta', 'Нова Пошта')]
    
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='new')
    shipping_type = models.CharField(max_length=20, choices=SHIPPING_CHOICES, default='pickup')
    full_name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    nova_poshta_branch = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self): return f"Замовлення #{self.id}"

    class Meta:
        verbose_name = "Замовлення"
        verbose_name_plural = "Замовлення"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)
    def get_cost(self): return self.price_at_purchase * self.quantity
    def __str__(self): return f"{self.quantity} x {self.product}"

    class Meta:
        verbose_name = "Товар у замовленні"
        verbose_name_plural = "Товари у замовленнях"

# --- 4. ДОДАТКОВІ ---
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_gallery/', blank=True, null=True)
    image_url = models.URLField(max_length=1024, blank=True, null=True)

    class Meta:
        verbose_name = "Фото галереї"
        verbose_name_plural = "Фото галереї"

class SiteBanner(models.Model):
    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to='banners/', blank=True, null=True, verbose_name="Фото (Файл)")
    image_url = models.URLField(max_length=1024, blank=True, null=True, verbose_name="Фото (Посилання)")
    link = models.CharField(max_length=500, blank=True, null=True, verbose_name="Куди вести при кліку")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.title

    class Meta:
        verbose_name = "Банер"
        verbose_name_plural = "Банери"

class AboutImage(models.Model):
    image = models.ImageField(upload_to='about_us/')
    image_url = models.URLField(max_length=1024, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Фото про нас"
        verbose_name_plural = "Фото про нас"
