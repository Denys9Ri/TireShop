from django.urls import path, re_path
from . import views

app_name = "store"

# Дозволені сезони в SEO URL
SEASON_RE = r"(zymovi|litni|vsesezonni)"

# Розмір: 205-55-r16
SIZE_RE = r"(?P<width>\d{3})-(?P<profile>\d{2})-r(?P<diameter>\d{2})"

# Бренд: michelin, goodyear, hankook-k435 і т.д.
BRAND_RE = r"(?P<brand_slug>[-a-zA-Z0-9_]+)"

urlpatterns = [
    # ГОЛОВНА КАТАЛОГУ
    path("", views.catalog_view, name="catalog"),

    # --- SEO MATRIX (порядок важливий: від складного до простого) ---
    # /shyny/michelin/zymovi/205-55-r16/
    re_path(rf"^shyny/{BRAND_RE}/(?P<season_slug>{SEASON_RE})/{SIZE_RE}/$", views.seo_matrix_view, name="seo_full"),

    # /shyny/zymovi/205-55-r16/
    re_path(rf"^shyny/(?P<season_slug>{SEASON_RE})/{SIZE_RE}/$", views.seo_matrix_view, name="seo_season_size"),

    # /shyny/michelin/zymovi/
    re_path(rf"^shyny/{BRAND_RE}/(?P<season_slug>{SEASON_RE})/$", views.seo_matrix_view, name="seo_brand_season"),

    # /shyny/205-55-r16/
    re_path(rf"^shyny/{SIZE_RE}/$", views.seo_matrix_view, name="seo_size"),

    # /shyny/zymovi/
    re_path(rf"^shyny/(?P<season_slug>{SEASON_RE})/$", views.seo_matrix_view, name="seo_season"),

    # /shyny/michelin/
    re_path(rf"^shyny/{BRAND_RE}/$", views.seo_matrix_view, name="seo_brand"),

    # --- ТОВАР ---
    path("product/<slug:slug>/", views.product_detail_view, name="product_detail"),

    # --- КОШИК ---
    path("cart/", views.cart_detail_view, name="cart_detail"),
    path("add/<int:product_id>/", views.cart_add_view, name="cart_add"),
    path("remove/<int:product_id>/", views.cart_remove_view, name="cart_remove"),
    path("update-quantity/<int:product_id>/", views.cart_update_quantity_view, name="cart_update_quantity"),
    path("checkout/", views.checkout_view, name="checkout"),

    # --- ІНФО ---
    path("about/", views.about_view, name="about"),
    path("contacts/", views.contacts_view, name="contacts"),
    path("delivery/", views.delivery_payment_view, name="delivery_payment"),
    path("warranty/", views.warranty_view, name="warranty"),

    # --- СЕРВІС ---
    path("sync-google-sheet/", views.sync_google_sheet_view, name="sync_google_sheet"),
    path("bot-callback/", views.bot_callback_view, name="bot_callback"),
]
