from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve 
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse # <--- ЦЕ ВАЖЛИВО

# Імпорт карт сайту
from store.sitemaps import ProductSitemap, StaticViewSitemap
from store.views import catalog_view, contacts_view, delivery_payment_view

sitemaps = {
    'products': ProductSitemap,
    'static': StaticViewSitemap,
}

# --- ФУНКЦІЯ ROBOTS.TXT (ПРЯМО В КОДІ) ---
def robots_txt(request):
    content = """User-agent: *
Allow: /

Disallow: /admin/
Disallow: /users/
Disallow: /accounts/
Disallow: /store/cart/
Disallow: /store/checkout/

Sitemap: https://r16.com.ua/sitemap.xml
"""
    return HttpResponse(content, content_type="text/plain")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', catalog_view, name='catalog'),
    path('contacts/', contacts_view, name='contacts'),
    path('delivery-and-payment/', delivery_payment_view, name='delivery_payment'),
    path('store/', include('store.urls')),
    path('users/', include('users.urls')),
    path('accounts/', include('django.contrib.auth.urls')), 
    
    # --- SEO ---
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt), # <--- ТУТ ВИКЛИКАЄМО ФУНКЦІЮ
]

# --- MEDIA FILES ---
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
]
