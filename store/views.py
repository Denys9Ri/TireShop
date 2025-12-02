from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Case, When, Value, IntegerField, Q
from django.db import transaction
from django.conf import settings 
import requests 
import re 

from .models import Product, Order, OrderItem, Brand, SiteBanner
from .cart import Cart
from users.models import UserProfile

# --- ФУНКЦІЯ: ВІДПРАВКА В TELEGRAM ---
def send_order_to_telegram(order):
    try:
        token = settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_CHAT_ID
        
        if not token or not chat_id: return

        message = f"🔥 <b>НОВЕ ЗАМОВЛЕННЯ #{order.id}</b>\n"
        message += f"📅 {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        message += f"👤 <b>Клієнт:</b> {order.full_name}\n"
        message += f"📞 <b>Телефон:</b> {order.phone}\n"
        if order.email: message += f"📧 <b>Email:</b> {order.email}\n"
        
        message += f"\n🚚 <b>Доставка:</b> {order.get_shipping_type_display()}\n"
        if order.shipping_type == 'nova_poshta':
            message += f"📍 {order.city}, {order.nova_poshta_branch}\n"
        
        message += "\n🛒 <b>ТОВАРИ:</b>\n"
        total_sum = 0
        for item in order.items.all():
            item_sum = item.price_at_purchase * item.quantity
            total_sum += item_sum
            message += f"🔹 {item.product.brand.name} {item.product.name}\n"
            message += f"   └ {item.quantity} шт. х {item.price_at_purchase} грн = <b>{item_sum} грн</b>\n"
            
        message += f"\n💰 <b>ЗАГАЛОМ: {total_sum} грн</b>"

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}
        requests.post(url, data=payload)
    except Exception as e:
        print(f"❌ Помилка відправки в Telegram: {e}")

# --- 1. КАТАЛОГ ---
def catalog_view(request):
    brands = Brand.objects.all().order_by('name')
    widths = Product.objects.values_list('width', flat=True).distinct().order_by('width')
    profiles = Product.objects.values_list('profile', flat=True).distinct().order_by('profile')
    diameters = Product.objects.values_list('diameter', flat=True).distinct().order_by('diameter')
    season_choices = Product.SEASON_CHOICES
    
    products = Product.objects.annotate(
        status_order=Case(
            When(stock_quantity__gt=0, then=Value(0)), 
            default=Value(1),
            output_field=IntegerField(),
        )
    )

    search_query = request.GET.get('query', '').strip()
    if search_query:
        clean_query = re.sub(r'[/\sR\-]', '', search_query, flags=re.IGNORECASE)
        digits_match = re.fullmatch(r'(\d{6,7})', clean_query)

        if digits_match:
             digits = digits_match.group(1)
             w = digits[:3]
             p = digits[3:5]
             d = digits[5:]
             products = products.filter(width=int(w), profile=int(p), diameter=int(d))
        else:
            products = products.filter(
                Q(name__icontains=search_query) | 
                Q(brand__name__icontains=search_query) |
                Q(description__icontains=search_query)
            )

    selected_brand = request.GET.get('brand')
    selected_width = request.GET.get('width')
    selected_profile = request.GET.get('profile')
    selected_diameter = request.GET.get('diameter')
    selected_season = request.GET.get('season')
    
    if selected_brand: products = products.filter(brand__id=selected_brand)
    if selected_width: products = products.filter(width=selected_width)
    if selected_profile: products = products.filter(profile=selected_profile)
    if selected_diameter: products = products.filter(diameter=selected_diameter)
    if selected_season: products = products.filter(seasonality=selected_season)
    
    products = products.order_by('status_order', 'brand__name', 'name')
    
    active_filters = [k for k in request.GET if k != 'page']
    show_banner = False
    banners = []
    
    if not active_filters:
        show_banner = True
        banners = SiteBanner.objects.filter(is_active=True).order_by('-created_at')

    paginator = Paginator(products, 12) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number) 

    query_params = request.GET.copy()
    if 'page' in query_params: del query_params['page']
    filter_query_string = query_params.urlencode()

    context = {
        'page_obj': page_obj,
        'filter_query_string': filter_query_string,
        'all_brands': brands,
        'all_widths': widths,
        'all_profiles': profiles,
        'all_diameters': diameters,
        'all_seasons': season_choices,
        'selected_brand': int(selected_brand) if selected_brand else None,
        'selected_width': int(selected_width) if selected_width else None,
        'selected_profile': int(selected_profile) if selected_profile else None,
        'selected_diameter': int(selected_diameter) if selected_diameter else None,
        'selected_season': selected_season,
        'search_query': search_query,
        'show_banner': show_banner,
        'banners': banners,
    }
    return render(request, 'store/catalog.html', context)

# --- 2. СТОРІНКА ТОВАРУ (ЗІ СХОЖИМИ) ---
def product_detail_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # Шукаємо схожі товари (той самий розмір і сезон)
    # exclude(id=product.id) - щоб не показувати цей самий товар у рекомендаціях
    similar_products = Product.objects.filter(
        width=product.width,
        profile=product.profile,
        diameter=product.diameter,
        seasonality=product.seasonality
    ).exclude(id=product.id)[:4] # Показуємо максимум 4 штуки

    context = {
        'product': product,
        'similar_products': similar_products
    }
    return render(request, 'store/product_detail.html', context)

# --- ІНФОРМАЦІЙНІ СТОРІНКИ ---
def contacts_view(request):
    return render(request, 'store/contacts.html')

def delivery_payment_view(request):
    return render(request, 'store/delivery_payment.html')

def warranty_view(request): # <--- НОВА СТОРІНКА ГАРАНТІЇ
    return render(request, 'store/warranty.html')

# --- КОШИК І ЗАМОВЛЕННЯ ---
def cart_detail_view(request):
    cart = Cart(request)
    return render(request, 'store/cart.html', {'cart': cart})

@require_POST
def cart_add_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    try: quantity = int(request.POST.get('quantity', 1))
    except: quantity = 1
    cart.add(product=product, quantity=max(1, quantity), update_quantity=False)
    return redirect(request.META.get('HTTP_REFERER', 'catalog'))

@require_POST
def cart_update_quantity_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    if quantity > 0: cart.add(product=product, quantity=quantity, update_quantity=True)
    else: cart.remove(product)
    return redirect('store:cart_detail') 

def cart_remove_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('store:cart_detail')

def checkout_view(request):
    cart = Cart(request)
    if len(cart) == 0: return redirect('catalog')

    profile = None
    prefill = {}
    if request.user.is_authenticated:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        prefill = {
            'full_name': f"{request.user.last_name} {request.user.first_name}".strip(),
            'email': request.user.email,
            'phone': profile.phone_primary,
            'city': profile.city,
            'nova_poshta_branch': profile.nova_poshta_branch,
            'pickup_name': f"{request.user.first_name} {request.user.last_name}".strip(),
            'pickup_phone': profile.phone_primary,
        }

    if request.method == 'POST':
        shipping_type = request.POST.get('shipping_type')
        is_pickup = shipping_type == 'pickup'
        full_name = request.POST.get('pickup_name') if is_pickup else request.POST.get('full_name')
        phone = request.POST.get('pickup_phone') if is_pickup else request.POST.get('phone')
        email = None if is_pickup else request.POST.get('email')
        city = "Київ, вул. Володимира Качали, 3" if is_pickup else request.POST.get('city')
        nova_poshta_branch = None if is_pickup else request.POST.get('nova_poshta_branch')
        
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
                order=order, product=item['product'],
                quantity=item['quantity'], price_at_purchase=item['price']
            )
        
        send_order_to_telegram(order)

        cart.clear()
        if request.user.is_authenticated and profile:
            if phone: profile.phone_primary = phone
            if not is_pickup:
                if city: profile.city = city
                if nova_poshta_branch: profile.nova_poshta_branch = nova_poshta_branch
            profile.save()

        if request.user.is_authenticated: return redirect('users:profile')
        return redirect('catalog')
    
    return render(request, 'store/checkout.html', {'prefill': prefill})

# --- АКВЕДУК ---
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
@transaction.atomic
def sync_google_sheet_view(request):
    # ... (код синхронізації залишається без змін) ...
    return redirect('admin:store_product_changelist')
