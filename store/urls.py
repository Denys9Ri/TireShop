from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # 1. ГОЛОВНА КАТАЛОГУ
    path('', views.catalog_view, name='catalog'),

    # --- 🏆 SEO MATRIX ---
    path('shyny/<str:brand_slug>/<str:season_slug>/<int:width>-<int:profile>-r<int:diameter>/', views.seo_matrix_view, name='seo_full'),
    path('shyny/<str:brand_slug>/<str:season_slug>/', views.seo_matrix_view, name='seo_brand_season'),
    path('shyny/<str:season_slug>/<int:width>-<int:profile>-r<int:diameter>/', views.seo_matrix_view, name='seo_season_size'),
    path('shyny/<str:season_slug>/', views.seo_matrix_view, name='seo_season'),
    path('shyny/<str:brand_slug>/', views.seo_matrix_view, name='seo_brand'),
    path('shyny/<int:width>-<int:profile>-r<int:diameter>/', views.seo_matrix_view, name='seo_size'),

    # --- ТОВАР ---
    # Новий шлях (Slug)
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),
    
    # 🔥 ВАЖЛИВО: РЕДИРЕКТ ДЛЯ СТАРИХ ПОСИЛАНЬ GOOGLE (ID -> SLUG) 🔥
    # Додаємо це, щоб Google не отримував 404
    path('product/<int:product_id>/', views.redirect_old_product_urls),

    # --- ФУНКЦІОНАЛ ---
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
