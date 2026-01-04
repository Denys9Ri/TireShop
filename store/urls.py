from django.urls import path, re_path  # 👈 Додали re_path
from . import views

app_name = 'store'

urlpatterns = [
    # 🔥 ГОЛОВНА ТА КАТАЛОГ 🔥
    path('', views.home_view, name='home'),
    path('catalog/', views.catalog_view, name='catalog'),

    # --- SEO MATRIX (Виправлений порядок) ---
    
    # 1. Лендінг бренду (shiny/brendy/michelin/)
    path('shiny/brendy/<str:brand_slug>/', views.brand_landing_view, name='brand_landing'),

    # 2. ПОВНА МАТРИЦЯ: Бренд + Сезон + Розмір
    # (shiny/michelin/zimovi/205-55-r16/)
    path('shiny/<str:brand_slug>/<str:season_slug>/<int:width>-<int:profile>-r<int:diameter>/', views.seo_matrix_view, name='seo_full'),

    # 3. 🔥 ФІКС 🔥: СЕЗОН + РОЗМІР
    # Використовуємо re_path, щоб перехопити ТІЛЬКИ зимові/літні/всесезонні
    # Цей рядок ОБОВ'ЯЗКОВО має бути ВИЩЕ, ніж seo_brand_size
    re_path(r'^shiny/(?P<season_slug>zimovi|litni|vsesezonni)/(?P<width>\d+)-(?P<profile>\d+)-r(?P<diameter>\d+)/$', views.seo_matrix_view, name='seo_season_size'),

    # 4. БРЕНД + РОЗМІР
    # Сюди потрапить все інше (наприклад, michelin/205-55-r16/), що не підпало під правило вище
    path('shiny/<str:brand_slug>/<int:width>-<int:profile>-r<int:diameter>/', views.seo_matrix_view, name='seo_brand_size'),

    # 5. БРЕНД + СЕЗОН
    # (shiny/michelin/zimovi/)
    path('shiny/<str:brand_slug>/<str:season_slug>/', views.seo_matrix_view, name='seo_brand_season'),

    # 6. ТІЛЬКИ РОЗМІР
    # (shiny/205-55-r16/)
    path('shiny/<int:width>-<int:profile>-r<int:diameter>/', views.seo_matrix_view, name='seo_size'),

    # 7. УНІВЕРСАЛЬНИЙ (Тільки Сезон АБО Тільки Бренд)
    # (shiny/zimovi/ АБО shiny/michelin/)
    path('shiny/<str:slug>/', views.seo_matrix_view, name='seo_universal'), 
    
    # Технічні дублі
    path('shiny/season/<str:slug>/', views.seo_matrix_view, name='seo_season'),
    path('shiny/brand/<str:slug>/', views.seo_matrix_view, name='seo_brand'),

    # --- ТОВАР, КОШИК, ІНШЕ ---
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('product/<int:product_id>/', views.redirect_old_product_urls),
    path('cart/', views.cart_detail_view, name='cart_detail'),
    path('add/<int:product_id>/', views.cart_add_view, name='cart_add'),
    path('cart/add-ajax/<int:product_id>/', views.cart_add_ajax_view, name='cart_add_ajax'),
    path('remove/<int:product_id>/', views.cart_remove_view, name='cart_remove'),
    path('update-quantity/<int:product_id>/', views.cart_update_quantity_view, name='cart_update_quantity'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('about/', views.about_view, name='about'),
    path('contacts/', views.contacts_view, name='contacts'),
    path('delivery/', views.delivery_payment_view, name='delivery_payment'),
    path('warranty/', views.warranty_view, name='warranty'),
    path('bot-callback/', views.bot_callback_view, name='bot_callback'),
    path('sync-google-sheet/', views.sync_google_sheet_view, name='sync_google_sheet'),
    path('faq/', views.faq_view, name='faq'),
    path('secret-fix-names/', views.fix_product_names_view),
    path('robots.txt', views.robots_txt),
]
