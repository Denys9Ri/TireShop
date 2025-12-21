from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve 
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from store.views import fix_product_names_view

# Імпортуємо Sitemap класи
from store.sitemaps import ProductSitemap, StaticViewSitemap

sitemaps = {
    'products': ProductSitemap,
    'static': StaticViewSitemap,
}

def robots_txt(request):
    content = "User-agent: *\nAllow: /\n\nSitemap: https://r16.com.ua/sitemap.xml"
    return HttpResponse(content, content_type="text/plain")

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 1. SEO СТОРІНКИ
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt),

    # 2. КОРИСТУВАЧІ (ВХІД/РЕЄСТРАЦІЯ)
    # Підключаємо наш оновлений users/urls.py
    path('users/', include('users.urls')), 
    
    # Якщо потрібно скидання паролю, залишаємо accounts, але users перекриє логін/логаут
    path('accounts/', include('django.contrib.auth.urls')), 

    # 3. МАГАЗИН (ГОЛОВНИЙ ДОДАТОК)
    # Підключаємо в корінь (''). Тепер store:catalog відповідає за Головну.
    path('', include('store.urls')),

    path('secret-fix-names/', fix_product_names_view),
]

# Медіа файли
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
    re_path(r'^static/(?P<path>.*)$', serve, {
        'document_root': settings.STATIC_ROOT,
    }),
]
