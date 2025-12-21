from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.db import models
import decimal
import re

# --- 0. НАЛАШТУВАННЯ ---
class SiteSettings(models.Model):
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
    slug = models.SlugField(max_length=100, unique=True, null=True, blank=True)
    image = models.ImageField("Логотип", upload_to='brands/', blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='budget')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:110]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


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
    
    # 🔥 ВАЖЛИВО: price тепер реальне поле, щоб працювали фільтри Min/Max 🔥
    price = models.DecimalField("Ціна продажу", max_digits=10, decimal_places=0, default=0)
    
    stock_quantity = models.IntegerField(default=0)
    discount_percent = models.IntegerField(default=0)
    
    photo_url = models.URLField(max_length=1024, blank=True, null=True)
    photo = models.ImageField(upload_to='products/', blank=True, null=True)

    @property
    def display_name(self):
        """
        Віртуальна назва для сайту:
        Прибирає Бренд, 'Шина' та Розмір, залишаючи тільки Модель та Індекси.
        """
        text = self.name
        
        # 1. Прибираємо "Шина"
        text = text.replace("Шина", "").replace("шина", "")
        
        # 2. Прибираємо назву Бренду (якщо вона є на початку або в дужках)
        if self.brand:
            # Case-insensitive заміна бренду на початку
            text = re.sub(f"^{self.brand.name}", "", text, flags=re.IGNORECASE)
            # Заміна (Brand)
            text = re.sub(f"\({self.brand.name}\)", "", text, flags=re.IGNORECASE)

        # 3. Прибираємо Розмір (195/65R15, 205/55 R16 тощо)
        # Шукаємо патерн: Цифри/Цифри[Буква]Цифри
        text = re.sub(r'\d{3}/\d{2}\s?[R|Z|r|z]\d{1,2}', '', text)

        # 4. Прибираємо зайві пробіли та символи по краях
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'^\W+|\W+$', '', text) # Прибирає коми/тире на початку і в кінці

        # Якщо раптом стерли все (буває таке), повертаємо оригінал, щоб не було пусто
        if not text:
            return self.name
            
        return text
        
    # Технічні характеристики
    country = models.CharField(max_length=50, blank=True, null=True)
    year = models.IntegerField(default=2024)
    load_index = models.CharField(max_length=10, blank=True, null=True)
    speed_index = models.CharField(max_length=10, blank=True, null=True)
    stud_type = models.CharField(max_length=50, default="Не шип")
    vehicle_type = models.CharField(max_length=50, default="Легковий")

    # Властивість для "Старої ціни" (щоб показувати закреслену ціну)
    @property
    def old_price(self):
        if self.discount_percent > 0:
            # Якщо є знижка, то price - це вже знижена ціна.
            # Нам треба повернути ціну ДО знижки.
            return int(self.price * 100 / (100 - self.discount_percent))
        return None

    # Авто-генерація SLUG та ЦІНИ при збереженні
    def save(self, *args, **kwargs):
        # 1. Генерація SLUG
        if not self.slug:
            b_name = self.brand.name if self.brand else 'no-brand'
            base_slug = f"{b_name}-{self.name}-{self.width}-{self.profile}-{self.diameter}"
            self.slug = slugify(base_slug)[:250]

        # 2. Розрахунок ЦІНИ (Фіксуємо в базу)
        try:
            settings = SiteSettings.get_solo()
            markup = decimal.Decimal(str(settings.global_markup))
        except:
            markup = decimal.Decimal('1.30')
        
        cost = decimal.Decimal(str(self.cost_price))
        
        # Базова ціна = Собівартість * Націнка
        base_price = cost * markup
        
        # Якщо є знижка - віднімаємо її
        if self.discount_percent > 0:
            factor = (decimal.Decimal('100') - decimal.Decimal(self.discount_percent)) / decimal.Decimal('100')
            final_price = base_price * factor
        else:
            final_price = base_price
            
        # Записуємо в реальне поле price (округлюємо до цілого)
        self.price = int(final_price)

        super().save(*args, **kwargs)

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
    link = models.CharField(max_length=500, blank=True, null=True, verbose_name="Куди вести при кліку")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self): return self.title

class AboutImage(models.Model):
    image = models.ImageField(upload_to='about_us/')
    image_url = models.URLField(max_length=1024, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
