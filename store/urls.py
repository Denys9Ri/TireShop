from django.urls import path
from . import views

# Цей 'app_name' допомагає Django розрізняти
# посилання, якщо у вас є інші додатки з такими ж назвами
app_name = 'store'

urlpatterns = [
    # Ми створимо ці 'views' (функції) у наступному кроці
    
    # /store/cart/
    path('cart/', views.cart_detail_view, name='cart_detail'),
    
    # /store/add/5/ (де 5 - це id товару)
    path('add/<int:product_id>/', views.cart_add_view, name='cart_add'),
    
    # /store/remove/5/
    path('remove/<int:product_id>/', views.cart_remove_view, name='cart_remove'),

    # /store/update-quantity/5/
    path('update-quantity/<int:product_id>/', views.cart_update_quantity_view, name='cart_update_quantity'),
    
    # /store/checkout/
    path('checkout/', views.checkout_view, name='checkout'),
]
