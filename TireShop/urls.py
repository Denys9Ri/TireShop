from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve # <--- Імпортуємо функцію для роздачі файлів

from store.views import catalog_view, contacts_view, delivery_payment_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', catalog_view, name='catalog'),
    path('contacts/', contacts_view, name='contacts'),
    path('delivery-and-payment/', delivery_payment_view, name='delivery_payment'),
    path('store/', include('store.urls')),
    path('users/', include('users.urls')),
    path('accounts/', include('django.contrib.auth.urls')), 
]

# --- МАГІЯ ДЛЯ RENDER ---
# Цей код змушує Django показувати завантажені фото
# навіть якщо DEBUG = False (як на сервері)
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
]
