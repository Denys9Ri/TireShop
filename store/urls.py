from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # 1. ГОЛОВНА / КАТАЛОГ
    path('', views.catalog_view, name='catalog'),
    
    # --- 🔥 НОВИЙ БЛОК SEO (Найвищий пріоритет) 🔥 ---
    
    # А) СЕЗОН + РОЗМІР (Наприклад: /shyny/zymovi/205-55-r16/)
    # Це найважливіші сторінки для продажу ("купити зимові шини 205 55 16")
    path('shyny/<str:season_slug>/<int:width>-<int:profile>-r<int:diameter>/', views.seo_landing_view, name='seo_season_size'),

    # Б) ТІЛЬКИ СЕЗОН (Наприклад: /shyny/zymovi/)
    # Це загальні категорії
    path('shyny/<str:season_slug>/', views.seo_landing_view, name='seo_season'),

    # В) ТІЛЬКИ РОЗМІР (Старий маршрут: /shyny/205-55-r16/)
    path('shyny/<int:width>-<int:profile>-r<int:diameter>/', views.seo_category_view, name='seo_category'),
    
    # --- КІНЕЦЬ БЛОКУ SEO ---

    # 3. СТОРІНКА ТОВАРУ
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),
    
    # --- ФУНКЦІОНАЛ МАГАЗИНУ (БЕЗ ЗМІН) ---
    path('cart/', views.cart_detail_view, name='cart_detail'),
    path('add/<int:product_id>/', views.cart_add_view, name='cart_add'),
    path('remove/<int:product_id>/', views.cart_remove_view, name='cart_remove'),
    path('update-quantity/<int:product_id>/', views.cart_update_quantity_view, name='cart_update_quantity'),
    
    path('checkout/', views.checkout_view, name='checkout'),
    
    # ІНФО СТОРІНКИ 
    path('about/', views.about_view, name='about'),
    path('contacts/', views.contacts_view, name='contacts'),
    path('delivery/', views.delivery_payment_view, name='delivery_payment'),
    path('warranty/', views.warranty_view, name='warranty'),
    
    # ІНСТРУМЕНТИ
    path('sync-google-sheet/', views.sync_google_sheet_view, name='sync_google_sheet'),
    path('bot-callback/', views.bot_callback_view, name='bot_callback'),
]
