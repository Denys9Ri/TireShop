from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Case, When, Value, IntegerField, Q
from django.conf import settings
from django.http import JsonResponse
from django.db import transaction
import json
import requests
import re

from .models import Product, Order, OrderItem, Brand, SiteBanner, AboutImage
from .cart import Cart
from users.models import UserProfile
from django.contrib import messages

# --- ТЕЛЕГРАМ ---
def send_telegram(message):
    try:
        token = settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_CHAT_ID
        if token and chat_id:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'})
    except: pass

# --- ДОПОМІЖНА: Базовий QuerySet ---
def get_base_products():
    # Фільтруємо сміття (нульові розміри)
    return Product.objects.filter(width__gt=0, diameter__gt=0).annotate(
        status_order=Case(When(stock_quantity__gt=0, then=Value(0)), default=Value(1), output_field=IntegerField())
    )

# --- 1. КАТАЛОГ (ЗВИЧАЙНИЙ) ---
def catalog_view(request):
    products = get_base_products()
    
    # Фільтри (Виключаємо 0 у списках)
    brands = Brand.objects.all().order_by('name')
    widths = Product.objects.filter(width__gt=0).values_list('width', flat=True).distinct().order_by('width')
    profiles = Product.objects.filter(profile__gt=0).values_list('profile', flat=True).distinct().order_by('profile')
    diameters = Product.objects.filter(diameter__gt=0).values_list('diameter', flat=True).distinct().order_by('diameter')
    
    # Пошук
    query = request.GET.get('query', '').strip()
    if query:
        clean = re.sub(r'[/\sR\-]', '', query, flags=re.IGNORECASE)
        match = re.fullmatch(r'(\d{6,7})', clean)
        if match:
            d = match.group(1)
            products = products.filter(width=int(d[:3]), profile=int(d[3:5]), diameter=int(d[5:]))
        else:
            products = products.filter(Q(name__icontains=query) | Q(brand__name__icontains=query))

    # Застосування фільтрів
    s_brand = request.GET.get('brand')
    s_season = request.GET.get('season')
    s_width = request.GET.get('width')
    s_profile = request.GET.get('profile')
    s_diameter = request.GET.get('diameter')
    
    if s_brand: products = products.filter(brand__id=s_brand)
    if s_season: products = products.filter(seasonality=s_season)
    if s_width: products = products.filter(width=s_width)
    if s_profile: products = products.filter(profile=s_profile)
    if s_diameter: products = products.filter(diameter=s_diameter)

    # Сортування
    ordering = request.GET.get('ordering')
    if ordering == 'cheap': products = products.filter(brand__category='budget').order_by('status_order', 'cost_price')
    elif ordering == 'medium': products = products.filter(brand__category='medium').order_by('status_order', 'cost_price')
    elif ordering == 'expensive': products = products.filter(brand__category='top').order_by('status_order', '-cost_price')
    else: products = products.order_by('status_order', 'brand__name', 'name')

    # Пагінація
    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    # SEO META
    seo_title = "Купити шини в Києві | R16.com.ua"
    seo_h1 = "Каталог шин"
    if query:
        seo_title = f"Результати пошуку: {query} | R16"
        seo_h1 = f"Пошук: {query}"

    q_params = request.GET.copy()
    if 'page' in q_params: del q_params['page']

    return render(request, 'store/catalog.html', {
        'page_obj': page_obj, 'filter_query_string': q_params.urlencode(),
        'all_brands': brands, 'all_widths': widths, 'all_profiles': profiles, 'all_diameters': diameters, 'all_seasons': Product.SEASON_CHOICES,
        'selected_brand': int(s_brand) if s_brand else None,
        'selected_season': s_season, 'selected_width': int(s_width) if s_width else None,
        'selected_profile': int(s_profile) if s_profile else None,
        'selected_diameter': int(s_diameter) if s_diameter else None,
        'search_query': query, 'banners': SiteBanner.objects.filter(is_active=True), 'show_banner': not (q_params or query),
        'seo_title': seo_title, 'seo_h1': seo_h1
    })

# --- 2. SEO ПОСАДКОВА СТОРІНКА (РОЗМІР) ---
def seo_category_view(request, width, profile, diameter):
    products = get_base_products().filter(width=width, profile=profile, diameter=diameter)
    
    # SEO Title: Купити шини 205/55 R16 — ціни, наявність | R16
    seo_title = f"Купити шини {width}/{profile} R{diameter} — ціни, наявність | R16"
    seo_h1 = f"Шини {width}/{profile} R{diameter}"
    
    # Фільтри для форми (щоб були заповнені)
    brands = Brand.objects.all().order_by('name')
    
    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'store/catalog.html', {
        'page_obj': page_obj, 'all_brands': brands, 
        'all_widths': Product.objects.filter(width__gt=0).values_list('width', flat=True).distinct().order_by('width'),
        'all_profiles': Product.objects.filter(profile__gt=0).values_list('profile', flat=True).distinct().order_by('profile'),
        'all_diameters': Product.objects.filter(diameter__gt=0).values_list('diameter', flat=True).distinct().order_by('diameter'),
        'all_seasons': Product.SEASON_CHOICES,
        'selected_width': width, 'selected_profile': profile, 'selected_diameter': diameter,
        'seo_title': seo_title, 'seo_h1': seo_h1,
        'is_seo_page': True 
    })

# --- 3. ТОВАР (ПО SLUG) ---
def product_detail_view(request, slug):
    product = get_object_or_404(Product, slug=slug)
    similar = Product.objects.filter(width=product.width, profile=product.profile, diameter=product.diameter).exclude(id=product.id)[:4]
    
    # SEO Title товару
    seo_title = f"{product.brand.name} {product.name} {product.width}/{product.profile} R{product.diameter} - Купити | R16"
    
    return render(request, 'store/product_detail.html', {
        'product': product, 'similar_products': similar, 'seo_title': seo_title
    })

# --- БОТ ---
@require_POST
def bot_callback_view(request):
    try:
        data = json.loads(request.body)
        phone = data.get('phone')
        if phone:
            send_telegram(f"🚨 <b>SOS! ЗАПИТ З БОТА</b>\nКлієнт просить допомоги.\n📞 {phone}")
            return JsonResponse({'status': 'ok'})
    except: pass
    return JsonResponse({'status': 'error'}, status=400)

# --- ІНШЕ ---
def cart_detail_view(request): return render(request, 'store/cart.html', {'cart': Cart(request)})
@require_POST
def cart_add_view(request, product_id):
    cart = Cart(request); product = get_object_or_404(Product, id=product_id)
    cart.add(product=product, quantity=int(request.POST.get('quantity', 1)))
    return redirect(request.META.get('HTTP_REFERER', 'store:catalog'))
@require_POST
def cart_update_quantity_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    
    try:
        qty = int(request.POST.get('quantity', 1))
        
        # 🔥 ПЕРЕВІРКА НАЯВНОСТІ 🔥
        if qty > product.stock_quantity:
            qty = product.stock_quantity # Обмежуємо максимумом
            messages.warning(request, f"Увага! Доступно лише {product.stock_quantity} шт. товару {product.brand.name} {product.name}.")
        
        if qty > 0:
            cart.add(product, qty, update_quantity=True)
        else:
            cart.remove(product)
            
    except ValueError:
        pass
        
    return redirect('store:cart_detail')
def cart_remove_view(request, product_id):
    cart = Cart(request); cart.remove(get_object_or_404(Product, id=product_id))
    return redirect('store:cart_detail')

def checkout_view(request):
    cart = Cart(request)
    if not cart: return redirect('store:catalog')
    if request.method == 'POST':
        is_pickup = request.POST.get('shipping_type') == 'pickup'
        order = Order.objects.create(
            customer=request.user if request.user.is_authenticated else None,
            shipping_type=request.POST.get('shipping_type'),
            full_name=request.POST.get('pickup_name' if is_pickup else 'full_name'),
            phone=request.POST.get('pickup_phone' if is_pickup else 'phone'),
            email=None if is_pickup else request.POST.get('email'),
            city="Київ, вул. Володимира Качали, 3" if is_pickup else request.POST.get('city'),
            nova_poshta_branch=None if is_pickup else request.POST.get('nova_poshta_branch')
        )
        for item in cart: 
            # get_cost тепер є в моделі OrderItem, тому це буде працювати
            price = item['price']
            qty = item['quantity']
            OrderItem.objects.create(order=order, product=item['product'], quantity=qty, price_at_purchase=price)
        
        # Рахуємо суму для телеграма
        total_sum = sum(item['price'] * item['quantity'] for item in cart)
        
        send_telegram(f"🔥 <b>ЗАМОВЛЕННЯ #{order.id}</b>\n👤 {order.full_name}\n📞 {order.phone}\n💰 {total_sum} грн")
        cart.clear()
        return redirect('users:profile' if request.user.is_authenticated else 'store:catalog')
    return render(request, 'store/checkout.html')

def about_view(request): return render(request, 'store/about.html')
def contacts_view(request): return render(request, 'store/contacts.html')
def delivery_payment_view(request): return render(request, 'store/delivery_payment.html')
def warranty_view(request): return render(request, 'store/warranty.html')

# 🔥 ОСЬ ВОНА - ПРОПУЩЕНА ФУНКЦІЯ! 🔥
@transaction.atomic
def sync_google_sheet_view(request):
    return redirect('admin:store_product_changelist')
