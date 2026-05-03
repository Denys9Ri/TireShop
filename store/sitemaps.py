from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product, Brand

class BrandSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        # 🔥 ОСЬ ГОЛОВНИЙ ФІКС: Відкидаємо бренди з пустим слагом
        return Brand.objects.exclude(slug__isnull=True).exclude(slug='')

    def location(self, obj):
        return reverse('store:brand_landing', args=[obj.slug])

class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        # 🔥 Відкидаємо товари з пустим слагом
        return Product.objects.exclude(slug__isnull=True).exclude(slug='')

    def location(self, obj):
        return reverse('store:product_detail', args=[obj.slug])

class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'monthly'

    def items(self):
        return [
            'store:home', 
            'store:catalog', 
            'store:about', 
            'store:contacts', 
            'store:delivery_payment', 
            'store:warranty', 
            'store:faq'
        ]

    def location(self, item):
        return reverse(item)

# Якщо у тебе були ще якісь класи (наприклад, для Сезонів), 
# просто переконайся, що в def items(self) немає пустих значень.
