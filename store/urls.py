from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # --- ТОВАР ---
    path('product/<int:product_id>/', views.product_detail_view, name='product_detail'),
    
    # --- КОШИК ---
    path('cart/', views.cart_detail_view, name='cart_detail'),
    path('add/<int:product_id>/', views.cart_add_view, name='cart_add'),
    path('remove/<int:product_id>/', views.cart_remove_view, name='cart_remove'),
    path('update-quantity/<int:product_id>/', views.cart_update_quantity_view, name='cart_update_quantity'),
    
    # --- ОФОРМЛЕННЯ ЗАМОВЛЕННЯ ---
    path('checkout/', views.checkout_view, name='checkout'),
    
    # --- ІНСТРУМЕНТИ (Синхронізація з Google Таблицями) ---
    path('sync-google-sheet/', views.sync_google_sheet_view, name='sync_google_sheet'),
]
