from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.catalog_view, name='catalog'),

    # --- SEO MATRIX (Всі можливі комбінації) ---
    
    # 1. 🔥 ПОВНА КОМБІНАЦІЯ (Бренд + Сезон + Розмір) 🔥
    # Приклад: /shiny/aplus/zimovi/205-55-r16/
    path('shiny/<str:brand_slug>/<str:season_slug>/<int:width>-<int:profile>-r<int:diameter>/', views.seo_matrix_view, name='seo_full'),
    
    # 2. Бренд + Розмір (Додано нове!)
    # Приклад: /shiny/sailun/215-60-r16/
    path('shiny/<str:brand_slug>/<int:width>-<int:profile>-r<int:diameter>/', views.seo_matrix_view, name='seo_brand_size'),

    # 3. Бренд + Сезон
    path('shiny/<str:brand_slug>/<str:season_slug>/', views.seo_matrix_view, name='seo_brand_season'),

    # 4. Сезон + Розмір
    path('shiny/<str:season_slug>/<int:width>-<int:profile>-r<int:diameter>/', views.seo_matrix_view, name='seo_season_size'),

    # 5. Просто Розмір
    path('shiny/<int:width>-<int:profile>-r<int:diameter>/', views.seo_matrix_view, name='seo_size'),
    
    # 6. Універсальний (Бренд або Сезон)
    path('shiny/<str:slug>/', views.seo_matrix_view, name='seo_universal'), 
    
    # Технічні дублі
    path('shiny/season/<str:slug>/', views.seo_matrix_view, name='seo_season'),
    path('shiny/brand/<str:slug>/', views.seo_matrix_view, name='seo_brand'),

    # --- ТОВАР ---
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('product/<int:product_id>/', views.redirect_old_product_urls),

    # --- КОШИК ---
    path('cart/', views.cart_detail_view, name='cart_detail'),
    path('add/<int:product_id>/', views.cart_add_view, name='cart_add'),
    path('cart/add-ajax/<int:product_id>/', views.cart_add_ajax_view, name='cart_add_ajax'),
    path('remove/<int:product_id>/', views.cart_remove_view, name='cart_remove'),
    path('update-quantity/<int:product_id>/', views.cart_update_quantity_view, name='cart_update_quantity'),
    
    # --- ОФОРМЛЕННЯ ТА ІНШЕ ---
    path('checkout/', views.checkout_view, name='checkout'),
    path('about/', views.about_view, name='about'),
    path('contacts/', views.contacts_view, name='contacts'),
    path('delivery/', views.delivery_payment_view, name='delivery_payment'),
    path('warranty/', views.warranty_view, name='warranty'),
    
    # --- СЕРВІСНІ ---
    path('bot-callback/', views.bot_callback_view, name='bot_callback'),
    path('sync-google-sheet/', views.sync_google_sheet_view, name='sync_google_sheet'),
    path('faq/', views.faq_view, name='faq'),
    path('secret-fix-names/', views.fix_product_names_view),
]
