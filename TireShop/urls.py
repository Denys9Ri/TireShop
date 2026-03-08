from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse

# Імпортуємо Views (🔥 Додав google_shopping_feed)
from store.views import fix_product_names_view, robots_txt, google_shopping_feed

# Імпортуємо Sitemap класи
from store.sitemaps import ProductSitemap, StaticViewSitemap, BrandSitemap

# Налаштування карти сайту
sitemaps = {
    'products': ProductSitemap,
    'static': StaticViewSitemap,
    'brands': BrandSitemap,  # Тепер Google бачитиме сторінки брендів
}

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 1. SEO СТОРІНКИ ТА ФІДИ
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt), # Використовуємо розумний robots.txt з store/views.py
    
    # 🔥 ОСЬ ВОНО: Підключення фіду для Google Merchant Center 🔥
    path('google-feed.xml', google_shopping_feed, name='google_shopping_feed'),

    # 2. КОРИСТУВАЧІ (ВХІД/РЕЄСТРАЦІЯ)
    path('users/', include('users.urls')), 
    path('accounts/', include('django.contrib.auth.urls')), 

    # 3. МАГАЗИН (ГОЛОВНИЙ ДОДАТОК)
    path('', include('store.urls')),

    # 4. СЛУЖБОВІ
    path('secret-fix-names/', fix_product_names_view),
]

# Медіа файли (Для Render та локальної розробки)
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
    re_path(r'^static/(?P<path>.*)$', serve, {
        'document_root': settings.STATIC_ROOT,
    }),
]
