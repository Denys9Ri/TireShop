from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Нам потрібно імпортувати вид (view) каталогу з нашого додатку 'store'
# Ми створимо цей view пізніше, але прописати шлях маємо вже зараз
from store.views import catalog_view

urlpatterns = [
    # 1. Адмін-панель (вона вже вбудована в Django)
    path('admin/', admin.site.urls),
    
    # 2. ГОЛОВНА СТОРІНКА (/)
    # Як ви і просили, вона одразу веде на 'catalog_view'
    path('', catalog_view, name='catalog'),
    
    # 3. Всі інші посилання магазину (кошик, замовлення і т.д.)
    # Ми "включаємо" всі посилання з файлу store/urls.py
    path('store/', include('store.urls')), 
    
    # 4. Кабінет клієнта (профіль, мої замовлення)
    # Ми "включаємо" всі посилання з файлу users/urls.py
    path('users/', include('users.urls')),
    
    # 5. Готові сторінки Django для входу/виходу/зміни пароля
    # Це дає нам /accounts/login/, /accounts/logout/ і т.д.
    path('accounts/', include('django.contrib.auth.urls')), 
]

# Це потрібно, щоб Django міг показувати фото товарів,
# які ви завантажите через адмінку (поки сайт в режимі розробки)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
