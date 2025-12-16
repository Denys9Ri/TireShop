from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.catalog_view, name='catalog'),

    # 1. Найдовші шляхи (Повна комбінація)
    path('shyny/<str:brand_slug>/<str:season_slug>/<int:width>-<int:profile>-r<int:diameter>/', views.seo_matrix_view, name='seo_full'),
    
    # 2. Шляхи "Бренд + Сезон"
    path('shyny/<str:brand_slug>/<str:season_slug>/', views.seo_matrix_view, name='seo_brand_season'),

    # 3. Шляхи "Сезон + Розмір"
    path('shyny/<str:season_slug>/<int:width>-<int:profile>-r<int:diameter>/', views.seo_matrix_view, name='seo_season_size'),

    # 4. Шляхи "Просто розмір"
    path('shyny/<int:width>-<int:profile>-r<int:diameter>/', views.seo_matrix_view, name='seo_size'),
    
    # 5. 🔥 УНІВЕРСАЛЬНИЙ ШЛЯХ (Тут була проблема!) 🔥
    # Цей шлях ловить І бренди (michelin), І сезони (zymovi)
    path('shyny/<str:slug>/', views.seo_matrix_view, name='seo_universal'), 
    
    # Дублюємо імена для зворотної сумісності (щоб хлібні крихти не ламались), 
    # але направляємо їх на той самий view
    path('shyny/season/<str:slug>/', views.seo_matrix_view, name='seo_season'), # Технічний дубль
    path('shyny/brand/<str:slug>/', views.seo_matrix_view, name='seo_brand'),   # Технічний дубль

    # Товар
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('product/<int:product_id>/', views.redirect_old_product_urls),

    # Інше
    path('cart/', views.cart_detail_view, name='cart_detail'),
    path('add/<int:product_id>/', views.cart_add_view, name='cart_add'),
    path('remove/<int:product_id>/', views.cart_remove_view, name='cart_remove'),
    path('update-quantity/<int:product_id>/', views.cart_update_quantity_view, name='cart_update_quantity'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('about/', views.about_view, name='about'),
    path('contacts/', views.contacts_view, name='contacts'),
    path('delivery/', views.delivery_payment_view, name='delivery_payment'),
    path('warranty/', views.warranty_view, name='warranty'),
    path('bot-callback/', views.bot_callback_view, name='bot_callback'),
    path('sync-google-sheet/', views.sync_google_sheet_view, name='sync_google_sheet'),
]
