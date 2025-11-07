from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
# Ми додали 'Brand' до списку імпорту
from .models import Product, Order, OrderItem, Brand
from .cart import Cart

# --- 1. ОНОВЛЕНИЙ КАТАЛОГ (з логікою фільтрів) ---
def catalog_view(request):
    # Починаємо з усіх товарів, сортуємо за брендом
    products = Product.objects.all().order_by('brand__name', 'name')
    
    # --- Логіка для заповнення фільтрів ---
    # Беремо тільки унікальні значення з бази
    brands = Brand.objects.all().order_by('name')
    widths = Product.objects.values_list('width', flat=True).distinct().order_by('width')
    profiles = Product.objects.values_list('profile', flat=True).distinct().order_by('profile')
    diameters = Product.objects.values_list('diameter', flat=True).distinct().order_by('diameter')
    season_choices = Product.SEASON_CHOICES

    # --- Логіка для обробки запиту фільтрації ---
    # Отримуємо вибрані значення з GET-запиту (з URL)
    selected_brand = request.GET.get('brand')
    selected_width = request.GET.get('width')
    selected_profile = request.GET.get('profile')
    selected_diameter = request.GET.get('diameter')
    selected_season = request.GET.get('season')

    # Застосовуємо фільтри, ЯКЩО вони були вибрані
    if selected_brand:
        products = products.filter(brand__id=selected_brand)
    if selected_width:
        products = products.filter(width=selected_width)
    if selected_profile:
        products = products.filter(profile=selected_profile)
    if selected_diameter:
        products = products.filter(diameter=selected_diameter)
    if selected_season:
        products = products.filter(seasonality=selected_season)

    # Збираємо всі дані, щоб відправити їх у HTML
    context = {
        'products': products,
        
        # Списки для заповнення <select> у фільтрі
        'all_brands': brands,
        'all_widths': widths,
        'all_profiles': profiles,
        'all_diameters': diameters,
        'all_seasons': season_choices,
        
        # Збережені значення, щоб фільтр "пам'ятав" вибір
        'selected_brand': int(selected_brand) if selected_brand else None,
        'selected_width': int(selected_width) if selected_width else None,
        'selected_profile': int(selected_profile) if selected_profile else None,
        'selected_diameter': int(selected_diameter) if selected_diameter else None,
        'selected_season': selected_season,
    }

    # "Малюємо" HTML-сторінку 'catalog.html', передаючи їй ВСІ ці дані
    return render(request, 'store/catalog.html', context)

# --- 2. СТОРІНКА КОШИКА (Без змін) ---
def cart_detail_view(request):
    cart = Cart(request)
    return render(request, 'store/cart.html', {'cart': cart})

# --- 3. ДОДАТИ В КОШИК (Без змін) ---
@require_POST
def cart_add_view(request, product_id):
    cart = Cart(request) 
    product = get_object_or_404(Product, id=product_id) 
    cart.add(product=product, quantity=1, update_quantity=False)
    # Повертаємо користувача на ту ж сторінку, з якої він додав товар
    # (Це краще, ніж завжди повертати в каталог)
    return redirect(request.META.get('HTTP_REFERER', 'catalog'))

# --- 4. ОНОВИТИ КІЛЬКІСТЬ (Без змін) ---
@require_POST
def cart_update_quantity_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity > 0:
        cart.add(product=product, quantity=quantity, update_quantity=True)
    else:
        cart.remove(product)
    return redirect('store:cart_detail') 

# --- 5. ВИДАЛИТИ З КОШИКА (Без змін) ---
def cart_remove_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('store:cart_detail')

# --- 6. ОФОРМЛЕННЯ ЗАМОВЛЕННЯ (Без змін) ---
def checkout_view(request):
    cart = Cart(request)
    if len(cart) == 0:
        return redirect('catalog')

    if request.method == 'POST':
        shipping_type = request.POST.get('shipping_type')
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        city = request.POST.get('city')
        nova_poshta_branch = request.POST.get('nova_poshta_branch')

        order = Order.objects.create(
            customer=request.user if request.user.is_authenticated else None,
            shipping_type=shipping_type,
            full_name=full_name,
            phone=phone,
            email=email,
            city=city,
            nova_poshta_branch=nova_poshta_branch,
            status='new'
        )

        for item in cart:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                quantity=item['quantity'],
                price_at_purchase=item['price'] 
            )
        
        cart.clear()
        
        # Тут краще створити сторінку 'order_success.html'
        # Але поки що повертаємо в кабінет (якщо залогінений) або в каталог
        if request.user.is_authenticated:
            return redirect('users:profile')
        return redirect('catalog') 

    return render(request, 'store/checkout.html', {})
