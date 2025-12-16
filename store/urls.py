from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # 1. ГОЛОВНА КАТАЛОГУ
    path('', views.catalog_view, name='catalog'),

    # --- 🏆 SEO MATRIX (В порядку від найскладнішого до найпростішого) ---
    
    # А) ПОВНИЙ ФУЛЛ: Бренд + Сезон + Розмір (Напр: /shyny/michelin/zymovi/205-55-r16/)
    path('shyny/<str:brand_slug>/<str:season_slug>/<int:width>-<int:profile>-r<int:diameter>/', views.seo_matrix_view, name='seo_full'),

    # Б) БРЕНД + СЕЗОН (Напр: /shyny/michelin/zymovi/)
    path('shyny/<str:brand_slug>/<str:season_slug>/', views.seo_matrix_view, name='seo_brand_season'),

    # В) СЕЗОН + РОЗМІР (Напр: /shyny/zymovi/205-55-r16/)
    path('shyny/<str:season_slug>/<int:width>-<int:profile>-r<int:diameter>/', views.seo_matrix_view, name='seo_season_size'),

    # Г) ТІЛЬКИ СЕЗОН (Напр: /shyny/zymovi/)
    path('shyny/<str:season_slug>/', views.seo_matrix_view, name='seo_season'),

    # Д) ТІЛЬКИ БРЕНД (Напр: /shyny/michelin/)
    path('shyny/<str:brand_slug>/', views.seo_matrix_view, name='seo_brand'),

    # Е) ТІЛЬКИ РОЗМІР (Напр: /shyny/205-55-r16/)
    path('shyny/<int:width>-<int:profile>-r<int:diameter>/', views.seo_matrix_view, name='seo_size'),

    # --- ТОВАР ---
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),

    # --- ФУНКЦІОНАЛ (Кошик і т.д.) ---
    path('cart/', views.cart_detail_view, name='cart_detail'),
    path('add/<int:product_id>/', views.cart_add_view, name='cart_add'),
    path('remove/<int:product_id>/', views.cart_remove_view, name='cart_remove'),
    path('update-quantity/<int:product_id>/', views.cart_update_quantity_view, name='cart_update_quantity'),
    path('checkout/', views.checkout_view, name='checkout'),
    
    # --- ІНФО ---
    path('about/', views.about_view, name='about'),
    path('contacts/', views.contacts_view, name='contacts'),
    path('delivery/', views.delivery_payment_view, name='delivery_payment'),
    path('warranty/', views.warranty_view, name='warranty'),
    
    # --- СЕРВІС ---
    path('sync-google-sheet/', views.sync_google_sheet_view, name='sync_google_sheet'),
    path('bot-callback/', views.bot_callback_view, name='bot_callback'),
]
