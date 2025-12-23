from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product, Brand

class StaticViewSitemap(Sitemap):
    """Статичні сторінки: Головна, Каталог, Контакти..."""
    priority = 0.5
    changefreq = 'daily'

    def items(self):
        # 🔥 ВИПРАВЛЕННЯ: Додали префікс 'store:' до всіх назв
        return [
            'store:catalog',
            'store:about',
            'store:contacts',
            'store:delivery_payment',
            'store:warranty',
            'store:faq',
        ]

    def location(self, item):
        return reverse(item)

class ProductSitemap(Sitemap):
    """Сторінки товарів"""
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        # 🔥 ВИПРАВЛЕННЯ: Додали .order_by('id'), щоб прибрати Warning
        return Product.objects.filter(stock_quantity__gt=0).order_by('id')

    def location(self, obj):
        return reverse('store:product_detail', args=[obj.slug])

class BrandSitemap(Sitemap):
    """🔥 НОВЕ: Сторінки брендів (Aplus, Michelin...)"""
    priority = 0.6
    changefreq = 'weekly'

    def items(self):
        return Brand.objects.all().order_by('name')

    def location(self, obj):
        # Генеруємо посилання типу /shiny/brendy/aplus/
        return reverse('store:brand_landing', args=[obj.slug])
