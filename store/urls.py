from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # 1. ГОЛОВНА / КАТАЛОГ (Він же кореневий шлях)
    path('', views.catalog_view, name='catalog'),
    
    # 2. SEO ПОСАДКОВІ СТОРІНКИ (Наприклад: /shyny/205-55-r16)
    # Цей маршрут повинен йти ПЕРЕД звичайним каталогом
    path('shyny/<int:width>-<int:profile>-r<int:diameter>/', views.seo_category_view, name='seo_category'),
    
    # 3. СТОРІНКА ТОВАРУ (По Slug, наприклад: /product/michelin-x-ice-205-55-16)
    # Ми міняємо його з /product/<int:product_id>/ на /product/<slug:slug>/
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),
    
    # --- СТАРІ ШЛЯХИ ---

    # КОШИК
    path('cart/', views.cart_detail_view, name='cart_detail'),
    path('add/<int:product_id>/', views.cart_add_view, name='cart_add'),
    path('remove/<int:product_id>/', views.cart_remove_view, name='cart_remove'),
    path('update-quantity/<int:product_id>/', views.cart_update_quantity_view, name='cart_update_quantity'),
    
    # ОФОРМЛЕННЯ ЗАМОВЛЕННЯ
    path('checkout/', views.checkout_view, name='checkout'),
    
    # ІНФО СТОРІНКИ 
    path('about/', views.about_view, name='about'),
    path('contacts/', views.contacts_view, name='contacts'),
    path('delivery/', views.delivery_payment_view, name='delivery_payment'),
    path('warranty/', views.warranty_view, name='warranty'),
    
    # ІНСТРУМЕНТИ (Синхронізація з Google Таблицями)
    path('sync-google-sheet/', views.sync_google_sheet_view, name='sync_google_sheet'),

    # БОТ (Зворотний дзвінок)
    path('bot-callback/', views.bot_callback_view, name='bot_callback'),
]
