from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product

class ProductSitemap(Sitemap):
    changefreq = "daily"  # Як часто змінюються товари
    priority = 0.9        # Пріоритетність (висока)

    def items(self):
        # Повертаємо в карту тільки товари, які є в наявності
        return Product.objects.filter(stock_quantity__gt=0)

    def location(self, obj):
        # Генерує посилання на кожен товар
        return reverse('store:product_detail', args=[obj.id])

class StaticViewSitemap(Sitemap):
    priority = 0.6
    changefreq = 'weekly'

    def items(self):
        # Назви сторінок, як вони записані в urls.py (name='...')
        return ['catalog', 'contacts', 'delivery_payment']

    def location(self, item):
        return reverse(item)
