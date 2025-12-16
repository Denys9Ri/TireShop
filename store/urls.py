from django.urls import path, re_path
from . import views

app_name = 'store'

SEASON_RE = r'(zymovi|litni|vsesezonni)'
SIZE_RE = r'(?P<width>\d{3})-(?P<profile>\d{2})-r(?P<diameter>\d{2})'
BRAND_RE = r'(?P<brand_slug>[-a-zA-Z0-9_]+)'

urlpatterns = [
    # Каталог з фільтрами (?season=...)
    path('', views.catalog_view, name='catalog'),

    # SEO MATRIX
    re_path(rf'^shyny/{BRAND_RE}/{SEASON_RE}/{SIZE_RE}/$', views.seo_matrix_view, name='seo_full'),
    re_path(rf'^shyny/{SEASON_RE}/{SIZE_RE}/$', views.seo_matrix_view, name='seo_season_size'),
    re_path(rf'^shyny/{BRAND_RE}/{SEASON_RE}/$', views.seo_matrix_view, name='seo_brand_season'),
    re_path(rf'^shyny/{SIZE_RE}/$', views.seo_matrix_view, name='seo_size'),
    re_path(rf'^shyny/{SEASON_RE}/$', views.seo_matrix_view, name='seo_season'),
    re_path(rf'^shyny/{BRAND_RE}/$', views.seo_matrix_view, name='seo_brand'),

    # Товар
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),

    # Кошик
    path('cart/', views.cart_detail_view, name='cart_detail'),
    path('add/<int:product_id>/', views.cart_add_view, name='cart_add'),
    path('remove/<int:product_id>/', views.cart_remove_view, name='cart_remove'),
    path('update-quantity/<int:product_id>/', views.cart_update_quantity_view, name='cart_update_quantity'),
    path('checkout/', views.checkout_view, name='checkout'),

    # Інфо
    path('about/', views.about_view, name='about'),
    path('contacts/', views.contacts_view, name='contacts'),
    path('delivery/', views.delivery_payment_view, name='delivery_payment'),
    path('warranty/', views.warranty_view, name='warranty'),

    # Сервіс
    path('sync-google-sheet/', views.sync_google_sheet_view, name='sync_google_sheet'),
    path('bot-callback/', views.bot_callback_view, name='bot_callback'),
]
