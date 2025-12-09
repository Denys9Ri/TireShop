from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Case, When, Value, IntegerField, Q
from django.db import transaction
from django.conf import settings 
import requests 
import re 

from .models import Product, Order, OrderItem, Brand, SiteBanner, AboutImage
from .cart import Cart
from users.models import UserProfile

# --- TELEGRAM ---
def send_order_to_telegram(order):
    try:
        token = settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_CHAT_ID
        if not token or not chat_id: return
        message = f"🔥 <b>НОВЕ ЗАМОВЛЕННЯ #{order.id}</b>\n"
        message += f"👤 {order.full_name}\n📞 {order.phone}\n"
        message += f"🚚 {order.get_shipping_type_display()}\n"
        if order.shipping_type == 'nova_poshta': message += f"📍 {order.city}, {order.nova_poshta_branch}\n"
        message += "\n🛒 <b>ТОВАРИ:</b>\n"
        total_sum = 0
        for item in order.items.all():
            item_sum = item.price_at_purchase * item.quantity
            total_sum += item_sum
            message += f"🔹 {item.product.brand.name} {item.product.name} ({item.quantity} шт)\n"
        message += f"\n💰 <b>СУМА: {total_sum} грн</b>"
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'})
    except Exception: pass

# --- КАТАЛОГ ---
def catalog_view(request):
    brands = Brand.objects.all().order_by('name')
    widths = Product.objects.values_list('width', flat=True).distinct().order_by('width')
    profiles = Product.objects.values_list('profile', flat=True).distinct().order_by('profile')
    diameters = Product.objects.values_list('diameter', flat=True).distinct().order_by('diameter')
    season_choices = Product.SEASON_CHOICES
    
    products = Product.objects.annotate(
        status_order=Case(When(stock_quantity__gt=0, then=Value(0)), default=Value(1), output_field=IntegerField())
    )

    # Пошук
    search_query = request.GET.get('query', '').strip()
    if search_query:
        clean_query = re.sub(r'[/\sR\-]', '', search_query, flags=re.IGNORECASE)
        digits_match = re.fullmatch(r'(\d{6,7})', clean_query)
        if digits_match:
             digits = digits_match.group(1)
             w, p, d = digits[:3], digits[3:5], digits[5:]
             products = products.filter(width=int(w), profile=int(p), diameter=int(d))
        else:
            products = products.filter(Q(name__icontains=search_query) | Q(brand__name__icontains=search_query))

    # Фільтри
    s_brand = request.GET.get('brand')
    s_width = request.GET.get('width')
    s_profile = request.GET.get('profile')
    s_diameter = request.GET.get('diameter')
    s_season = request.GET.get('season')
    
    if s_brand: products = products.filter(brand__id=s_brand)
    if s_width: products = products.filter(width=s_width)
    if s_profile: products = products.filter(profile=s_profile)
    if s_diameter: products = products.filter(diameter=s_diameter)
    if s_season: products = products.filter(seasonality=s_season)
    
    # Сортування (стандартне, щоб не було помилок)
    products = products.order_by('status_order', 'brand__name', 'name')
    
    # Банер
    active_filters = [k for k in request.GET if k != 'page']
    show_banner = not active_filters
    banners = SiteBanner.objects.filter(is_active=True).order_by('-created_at') if show_banner else []

    # Пагінація
    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    q_params = request.GET.copy()
    if 'page' in q_params: del q_params['page']

    context = {
        'page_obj': page_obj, 'filter_query_string': q_params.urlencode(),
        'all_brands': brands, 'all_widths': widths, 'all_profiles': profiles, 
        'all_diameters': diameters, 'all_seasons': season_choices,
        'selected_brand': int(s_brand) if s_brand else None,
        'selected_width': int(s_width) if s_width else None,
        'selected_profile': int(s_profile) if s_profile else None,
        'selected_diameter': int(s_diameter) if s_diameter else None,
        'selected_season': s_season, 'search_query': search_query,
        'show_banner': show_banner, 'banners': banners,
    }
    return render(request, 'store/catalog.html', context)

# --- ІНШІ VIEW (Без змін) ---
def product_detail_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    similar = Product.objects.filter(width=product.width, profile=product.profile, diameter=product.diameter).exclude(id=product.id)[:4]
    return render(request, 'store/product_detail.html', {'product': product, 'similar_products': similar})

def contacts_view(request): return render(request, 'store/contacts.html')
def delivery_payment_view(request): return render(request, 'store/delivery_payment.html')
def warranty_view(request): return render(request, 'store/warranty.html')
def about_view(request): return render(request, 'store/about.html', {'images': AboutImage.objects.all()})

def cart_detail_view(request): return render(request, 'store/cart.html', {'cart': Cart(request)})

@require_POST
def cart_add_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.add(product=product, quantity=int(request.POST.get('quantity', 1)))
    return redirect(request.META.get('HTTP_REFERER', 'catalog'))

@require_POST
def cart_update_quantity_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    qty = int(request.POST.get('quantity', 1))
    if qty > 0: cart.add(product, qty, update_quantity=True)
    else: cart.remove(product)
    return redirect('store:cart_detail')

def cart_remove_view(request, product_id):
    cart = Cart(request)
    cart.remove(get_object_or_404(Product, id=product_id))
    return redirect('store:cart_detail')

def checkout_view(request):
    cart = Cart(request)
    if not cart: return redirect('catalog')
    
    prefill = {}
    if request.user.is_authenticated:
        p, _ = UserProfile.objects.get_or_create(user=request.user)
        prefill = {'full_name': request.user.get_full_name(), 'phone': p.phone_primary, 'email': request.user.email, 'city': p.city, 'branch': p.nova_poshta_branch}

    if request.method == 'POST':
        # (Логіка збереження замовлення - стандартна)
        is_pickup = request.POST.get('shipping_type') == 'pickup'
        order = Order.objects.create(
            customer=request.user if request.user.is_authenticated else None,
            shipping_type=request.POST.get('shipping_type'),
            full_name=request.POST.get('pickup_name' if is_pickup else 'full_name'),
            phone=request.POST.get('pickup_phone' if is_pickup else 'phone'),
            email=None if is_pickup else request.POST.get('email'),
            city="Київ, вул. Володимира Качали, 3" if is_pickup else request.POST.get('city'),
            nova_poshta_branch=None if is_pickup else request.POST.get('nova_poshta_branch'),
            status='new'
        )
        for item in cart:
            OrderItem.objects.create(order=order, product=item['product'], quantity=item['quantity'], price_at_purchase=item['price'])
        send_order_to_telegram(order)
        cart.clear()
        return redirect('users:profile' if request.user.is_authenticated else 'catalog')

    return render(request, 'store/checkout.html', {'prefill': prefill})

@transaction.atomic
def sync_google_sheet_view(request): return redirect('admin:store_product_changelist')
