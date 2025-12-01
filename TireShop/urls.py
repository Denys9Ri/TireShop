from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve 
from django.contrib.sitemaps.views import sitemap # <--- Імпорт для карти сайту
from django.views.generic.base import TemplateView # <--- Імпорт для Robots.txt

# Імпортуємо наші карти (потрібен файл store/sitemaps.py)
from store.sitemaps import ProductSitemap, StaticViewSitemap
from store.views import catalog_view, contacts_view, delivery_payment_view

# Налаштування карти
sitemaps = {
    'products': ProductSitemap,
    'static': StaticViewSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', catalog_view, name='catalog'),
    path('contacts/', contacts_view, name='contacts'),
    path('delivery-and-payment/', delivery_payment_view, name='delivery_payment'),
    path('store/', include('store.urls')),
    path('users/', include('users.urls')),
    path('accounts/', include('django.contrib.auth.urls')), 
    
    # --- SEO: КАРТА САЙТУ ---
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),

    # --- SEO: ROBOTS.TXT ---
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
]

# --- МАГІЯ ДЛЯ RENDER ---
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
]
