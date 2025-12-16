from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve 
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse

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
    
    # 1. СЕРВІСНІ СТОРІНКИ (SEO)
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt),

    # 2. КОРИСТУВАЧІ ТА АВТОРИЗАЦІЯ
    # Важливо: users має бути перед store, щоб не перекриватись
    path('users/', include('users.urls')), 
    path('accounts/', include('django.contrib.auth.urls')), 

    # 3. МАГАЗИН (ГОЛОВНИЙ ДОДАТОК)
    # Ми підключаємо його в корінь (''), а не в 'store/'
    # Тепер store:catalog буде вести на головну сторінку "/"
    path('', include('store.urls')),
]

# Медіа файли (для локальної розробки та Render, якщо налаштовано whiteoise/serve)
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
    re_path(r'^static/(?P<path>.*)$', serve, {
        'document_root': settings.STATIC_ROOT,
    }),
]
