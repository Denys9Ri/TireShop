from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .models import Product, Order, OrderItem
from .cart import Cart

# --- 1. КАТАЛОГ (Головна сторінка) ---
# Цю функцію ми вже "прописали" в головному TireShop/urls.py
def catalog_view(request):
    # Беремо ВСІ товари з бази даних
    products = Product.objects.all()
    # "Малюємо" HTML-сторінку 'catalog.html', передаючи їй список товарів
    return render(request, 'store/catalog.html', {'products': products})

# --- 2. СТОРІНКА КОШИКА ---
def cart_detail_view(request):
    cart = Cart(request)
    # "Малюємо" сторінку 'cart.html', передаючи їй об'єкт кошика
    return render(request, 'store/cart.html', {'cart': cart})

# --- 3. ДОДАТИ В КОШИК ---
@require_POST # Дозволяє цій функції приймати лише POST-запити (з форм)
def cart_add_view(request, product_id):
    cart = Cart(request) # Отримуємо кошик з сесії
    product = get_object_or_404(Product, id=product_id) # Знаходимо товар
    
    # Додаємо товар в кошик (логіка з cart.py)
    cart.add(product=product, quantity=1, update_quantity=False)
    
    # Повертаємо користувача назад в каталог
    return redirect('catalog') # 'catalog' - це name= з TireShop/urls.py

# --- 4. ОНОВИТИ КІЛЬКІСТЬ В КОШИКУ ---
@require_POST
def cart_update_quantity_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    
    # Отримуємо нову кількість з форми
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity > 0:
        cart.add(product=product, quantity=quantity, update_quantity=True)
    else:
        # Якщо користувач ввів 0 або менше, видаляємо товар
        cart.remove(product)
        
    # Повертаємо користувача на сторінку кошика
    return redirect('store:cart_detail') # 'store:cart_detail' - app_name + name

# --- 5. ВИДАЛИТИ З КОШИКА ---
def cart_remove_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('store:cart_detail')

# --- 6. ОФОРМЛЕННЯ ЗАМОВЛЕННЯ ---
def checkout_view(request):
    cart = Cart(request)
    if len(cart) == 0:
        # Не можна оформлювати порожній кошик
        return redirect('catalog')

    if request.method == 'POST':
        # --- Обробка заповненої форми ---
        # 1. Отримуємо дані з форми (request.POST)
        shipping_type = request.POST.get('shipping_type')
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        city = request.POST.get('city')
        nova_poshta_branch = request.POST.get('nova_poshta_branch')

        # 2. Створюємо НОВЕ замовлення в базі даних
        order = Order.objects.create(
            # Якщо юзер залогінений, прив'язуємо замовлення до нього
            customer=request.user if request.user.is_authenticated else None,
            shipping_type=shipping_type,
            full_name=full_name,
            phone=phone,
            email=email,
            city=city,
            nova_poshta_branch=nova_poshta_branch,
            status='new' # Новий статус
        )

        # 3. Копіюємо товари з кошика в це замовлення
        for item in cart:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                quantity=item['quantity'],
                price_at_purchase=item['price'] # Зберігаємо ціну (з націнкою)
            )
        
        # 4. Очищуємо кошик
        cart.clear()
        
        # 5. Дякуємо і відправляємо (наприклад, назад в каталог)
        # В ідеалі - на сторінку "Дякуємо за замовлення" або в кабінет
        return redirect('catalog') # Поки що повертаємо в каталог

    # Якщо це GET-запит (користувач просто зайшов на сторінку),
    # показуємо йому порожню форму
    return render(request, 'store/checkout.html', {})
