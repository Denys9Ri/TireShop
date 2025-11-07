from django.db import models
from django.contrib.auth.models import User
import decimal

# --- Креслення 1: Шина (Товар) ---

class Product(models.Model):
    # Вибір для сезонності
    SEASON_CHOICES = [
        ('winter', 'Зимові'),
        ('summer', 'Літні'),
        ('all-season', 'Всесезонні'),
    ]

    name = models.CharField(max_length=255, verbose_name="Назва шини")
    photo = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Фото")
    size = models.CharField(max_length=50, verbose_name="Розмір (напр. 205/55 R16)")
    seasonality = models.CharField(max_length=20, choices=SEASON_CHOICES, verbose_name="Сезонність")
    
    # ВАЖЛИВО: Це ціна, яка буде у вашому "прайсі" (закупка)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ціна з прайсу (закупка)")

    # --- Ось ваша магія 30% націнки ---
    @property
    def price(self):
        # Розраховуємо ціну для клієнта
        markup = decimal.Decimal('1.30') # 1.0 + 0.30 = 30% націнки
        display_price = self.cost_price * markup
        # Округлюємо до 2 знаків після коми (як копійки)
        return display_price.quantize(decimal.Decimal('0.01'))

    def __str__(self):
        # Це те, як товар буде підписаний в адмінці
        return f"{self.name} ({self.size})"

# --- Креслення 2: Замовлення ---

class Order(models.Model):
    # Вибір для статусу замовлення (для адмінки і клієнта)
    STATUS_CHOICES = [
        ('new', 'Нове замовлення'),
        ('processing', 'В обробці'),
        ('shipped', 'Відправлено'),
        ('completed', 'Завершено'),
        ('canceled', 'Скасовано'),
    ]
    SHIPPING_CHOICES = [
        ('pickup', 'Самовивіз'),
        ('nova_poshta', 'Нова Пошта'),
    ]

    # 'customer' - це зареєстрований клієнт з кабінету
    # 'on_delete=models.SET_NULL' означає, що якщо клієнт видалить акаунт, замовлення залишиться
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Клієнт")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата створення")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Статус")
    
    # --- Дані для доставки ---
    shipping_type = models.CharField(max_length=20, choices=SHIPPING_CHOICES, default='pickup', verbose_name="Тип доставки")
    
    # Поля для Нової Пошти (можуть бути порожніми, якщо самовивіз)
    full_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="ПІБ отримувача")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Телефон")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Місто/Село")
    nova_poshta_branch = models.CharField(max_length=100, blank=True, null=True, verbose_name="Відділення НП")

    def __str__(self):
        return f"Замовлення #{self.id} від {self.created_at.strftime('%Y-%m-%d')}"

# --- Креслення 3: Позиція в замовленні ---
# (потрібно, щоб зв'язати Товар і Замовлення)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name="Замовлення")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, verbose_name="Товар")
    quantity = models.IntegerField(default=1, verbose_name="Кількість")
    
    # Ми зберігаємо ціну тут на випадок, якщо ціна товару в прайсі потім зміниться
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ціна (на момент покупки)")

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
