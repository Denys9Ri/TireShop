from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # 🔥 НОВА ГОЛОВНА СТОРІНКА 🔥
    path('', views.home_view, name='home'),

    # 📂 КАТАЛОГ (Тепер тут живе повний список)
    path('catalog/', views.catalog_view, name='catalog'),

    # --- SEO MATRIX (Фільтри) ---
    path('shiny/brendy/<str:brand_slug>/', views.brand_landing_view, name='brand_landing'),
    path('shiny/<str:brand_slug>/<str:season_slug>/<int:width>-<int:profile>-r<int:diameter>/', views.seo_matrix_view, name='seo_full'),
    path('shiny/<str:brand_slug>/<int:width>-<int:profile>-r<int:diameter>/', views.seo_matrix_view, name='seo_brand_size'),
    path('shiny/<str:brand_slug>/<str:season_slug>/', views.seo_matrix_view, name='seo_brand_season'),
    path('shiny/<str:season_slug>/<int:width>-<int:profile>-r<int:diameter>/', views.seo_matrix_view, name='seo_season_size'),
    path('shiny/<int:width>-<int:profile>-r<int:diameter>/', views.seo_matrix_view, name='seo_size'),
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
