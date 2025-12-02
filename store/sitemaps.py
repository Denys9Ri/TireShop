from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product

class ProductSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        # Повертаємо в карту тільки товари, які є в наявності
        return Product.objects.filter(stock_quantity__gt=0)

    def location(self, obj):
        return reverse('store:product_detail', args=[obj.id])

class StaticViewSitemap(Sitemap):
    priority = 0.6
    changefreq = 'weekly'

    def items(self):
        # Тут перелічені назви (name='...') з вашого urls.py
        return [
            'catalog',
            'contacts',
            'delivery_payment',
            'warranty',  # Нова сторінка гарантії
        ]

    def location(self, item):
        return reverse(item)
