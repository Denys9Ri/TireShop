from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Case, When, Value, IntegerField, Min, Count, Q
from django.conf import settings
from django.http import JsonResponse, Http404
from django.db import transaction
from django.urls import reverse
import json
import requests
import re

# Імпорти
from .cart import Cart 
from .models import Product, Order, OrderItem, Brand, SiteBanner

# --- CONFIG ---
SEASONS_MAP = {
    'zymovi': {'db': 'winter', 'ua': 'Зимові шини', 'adj': 'зимові'},
    'litni': {'db': 'summer', 'ua': 'Літні шини', 'adj': 'літні'},
    'vsesezonni': {'db': 'all_season', 'ua': 'Всесезонні шини', 'adj': 'всесезонні'}
}

# --- ДОПОМІЖНІ ФУНКЦІЇ ---

def send_telegram(message):
    try:
        token = settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_CHAT_ID
        if token and chat_id:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'})
    except: pass

def get_base_products():
    return Product.objects.filter(width__gt=0, diameter__gt=0).annotate(
        status_order=Case(When(stock_quantity__gt=0, then=Value(0)), default=Value(1), output_field=IntegerField())
    )

def generate_seo_meta(brand_obj=None, season_slug=None, w=None, p=None, d=None, min_price=0):
    parts = []
    season_info = SEASONS_MAP.get(season_slug)
    
    if season_info: parts.append(season_info['ua'])
    else: parts.append("Шини")
    
    if brand_obj: parts.append(brand_obj.name)
    
    size_str = ""
    if w and p and d:
        size_str = f"{w}/{p} R{d}"
        parts.append(size_str)
    
    h1 = " ".join(parts)
    title = f"Купити {h1} — ціна від {min_price} грн | Київ, Україна | R16"
    
    season_adj = season_info['adj'] if season_info else "якісні"
    brand_name = brand_obj.name if brand_obj else "світових брендів"
    desc = (
        f"✅ {h1} в наявності! 💰 Ціна від {min_price} грн. "
        f"🚚 Доставка по Україні. Великий вибір {season_adj} гуми {brand_name} {size_str}. "
        f"Гарантія якості, знижки, професійний підбір."
    )

    return {'title': title, 'h1': h1, 'description': desc}

def get_faq_schema(h1_title, min_price, count):
    if count == 0: return None
    faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f"Яка ціна на {h1_title}?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"Ціна на {h1_title} в нашому магазині починається від {min_price} грн. Актуальні ціни та наявність перевіряйте в каталозі."
                }
            },
            {
                "@type": "Question",
                "name": "Чи є доставка по Україні?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Так, ми здійснюємо доставку Новою Поштою в Київ, Харків, Одесу, Львів, Дніпро та інші міста України."
                }
            },
            {
                "@type": "Question",
                "name": "Чи надаєте ви гарантію?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Так, на всі шини діє заводська гарантія. Також можливе повернення або обмін протягом 14 днів."
                }
            }
        ]
    }
    return json.dumps(faq)

def get_cross_links(current_season_slug, current_brand, w, p, d):
    links = []
    if current_season_slug and not w:
        top_sizes = [(175,70,13), (185,65,14), (195,65,15), (205,55,16), (215,60,16), (225,45,17), (235,55,18)]
        group = {'title': 'Популярні розміри:', 'items': []}
        for sw, sp, sd in top_sizes:
            url = reverse('store:seo_season_size', args=[current_season_slug, sw, sp, sd])
            group['items'].append({'text': f"R{sd} {sw}/{sp}", 'url': url})
        links.append(group)

    if w and p and d:
        brands_qs = Brand.objects.filter(product__width=w, product__profile=p, product__diameter=d).distinct()[:10]
        if brands_qs:
            group = {'title': 'Популярні бренди в цьому розмірі:', 'items': []}
            for b in brands_qs:
                try:
                    if current_season_slug:
                        url = reverse('store:seo_full', args=[b.name, current_season_slug, w, p, d])
                    else:
                        url = reverse('store:seo_brand', args=[b.name])
                    group['items'].append({'text': b.name, 'url': url})
                except: pass
            links.append(group)
            
    if current_brand:
        group = {'title': f'Інші сезони {current_brand.name}:', 'items': []}
        for slug, info in SEASONS_MAP.items():
            if slug != current_season_slug:
                url = reverse('store:seo_brand_season', args=[current_brand.name, slug])
                group['items'].append({'text': info['ua'], 'url': url})
        links.append(group)
    return links

# --- 🔥 ГОЛОВНИЙ КОНТРОЛЕР (SEO MATRIX) 🔥 ---
def seo_matrix_view(request, brand_slug=None, season_slug=None, width=None, profile=None, diameter=None):
    products = get_base_products()
    brand_obj = None

    if brand_slug:
        brand_obj = Brand.objects.filter(name__iexact=brand_slug).first()
        if brand_obj: products = products.filter(brand=brand_obj)

    season_db = None
    if season_slug:
        if season_slug in SEASONS_MAP:
            season_db = SEASONS_MAP[season_slug]['db']
            products = products.filter(seasonality=season_db)
        else: raise Http404

    if width and profile and diameter:
        products = products.filter(width=width, profile=profile, diameter=diameter)

    stats = products.aggregate(min_price=Min('price'), count=Count('id'))
    min_price = stats['min_price'] if stats['min_price'] else 0
    prod_count = stats['count']

    seo_data = generate_seo_meta(brand_obj, season_slug, width, profile, diameter, int(min_price))
    faq_schema = get_faq_schema(seo_data['h1'], int(min_price), prod_count)
    cross_links = get_cross_links(season_slug, brand_obj, width, profile, diameter)

    brands = Brand.objects.all().order_by('name')
    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'store/catalog.html', {
        'page_obj': page_obj, 'all_brands': brands,
        'all_widths': Product.objects.filter(width__gt=0).values_list('width', flat=True).distinct().order_by('width'),
        'all_profiles': Product.objects.filter(profile__gt=0).values_list('profile', flat=True).distinct().order_by('profile'),
        'all_diameters': Product.objects.filter(diameter__gt=0).values_list('diameter', flat=True).distinct().order_by('diameter'),
        'all_seasons': Product.SEASON_CHOICES,
        
        'selected_brand_id': brand_obj.id if brand_obj else None,
        'selected_season': season_db,
        'selected_width': width, 'selected_profile': profile, 'selected_diameter': diameter,
        
        'seo_title': seo_data['title'],
        'seo_h1': seo_data['h1'],
        'seo_description': seo_data['description'],
        'faq_schema': faq_schema,
        'cross_links': cross_links,
        'is_seo_page': True
    })

# --- ЗВИЧАЙНИЙ КАТАЛОГ ---
def catalog_view(request):
    products = get_base_products()
    
    brands = Brand.objects.all().order_by('name')
    widths = Product.objects.filter(width__gt=0).values_list('width', flat=True).distinct().order_by('width')
    profiles = Product.objects.filter(profile__gt=0).values_list('profile', flat=True).distinct().order_by('profile')
    diameters = Product.objects.filter(diameter__gt=0).values_list('diameter', flat=True).distinct().order_by('diameter')
    
    query = request.GET.get('query', '').strip()
    if query:
        clean = re.sub(r'[/\sR\-]', '', query, flags=re.IGNORECASE)
        match = re.fullmatch(r'(\d{6,7})', clean)
        if match:
            d = match.group(1)
            products = products.filter(width=int(d[:3]), profile=int(d[3:5]), diameter=int(d[5:]))
        else:
            products = products.filter(Q(name__icontains=query) | Q(brand__name__icontains=query))

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

    ordering = request.GET.get('ordering')
    if ordering == 'cheap': products = products.filter(brand__category='budget').order_by('status_order', 'cost_price')
    elif ordering == 'medium': products = products.filter(brand__category='medium').order_by('status_order', 'cost_price')
    elif ordering == 'expensive': products = products.filter(brand__category='top').order_by('status_order', '-cost_price')
    else: products = products.order_by('status_order', 'brand__name', 'name')

    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    q_params = request.GET.copy()
    if 'page' in q_params: del q_params['page']

    return render(request, 'store/catalog.html', {
        'page_obj': page_obj, 'filter_query_string': q_params.urlencode(),
        'all_brands': brands, 'all_widths': widths, 'all_profiles': profiles, 'all_diameters': diameters, 'all_seasons': Product.SEASON_CHOICES,
        
        'selected_brand_id': int(s_brand) if s_brand else None,
        'selected_season': s_season, 'selected_width': int(s_width) if s_width else None,
        'selected_profile': int(s_profile) if s_profile else None,
        'selected_diameter': int(s_diameter) if s_diameter else None,
        
        'search_query': query, 'banners': SiteBanner.objects.filter(is_active=True), 'show_banner': not (q_params or query),
        'seo_title': "Каталог шин | R16.com.ua", 'seo_h1': "Всі шини"
    })

# --- ТОВАР (PRODUCT DETAIL) ---
# 🔥 ВИПРАВЛЕНО: Хлібні крихти тепер показують тільки "Зимові шини" (короткий шлях)
def product_detail_view(request, slug):
    product = get_object_or_404(Product, slug=slug)
    similar = Product.objects.filter(width=product.width, profile=product.profile, diameter=product.diameter).exclude(id=product.id)[:4]
    seo_title = f"{product.brand.name} {product.name} {product.width}/{product.profile} R{product.diameter} - Купити | R16"
    
    parent_category = None
    
    # 1. Знаходимо сезон (наприклад 'zymovi')
    season_slug = None
    for k, v in SEASONS_MAP.items():
        if v['db'] == product.seasonality:
            season_slug = k
            break
            
    # 2. Формуємо коротку хлібну крихту: Головна -> Каталог -> [Зимові Шини] -> Товар
    if season_slug:
        url = reverse('store:seo_season', args=[season_slug])
        name = SEASONS_MAP[season_slug]['ua'] # "Зимові шини"
        parent_category = {'name': name, 'url': url}

    return render(request, 'store/product_detail.html', {
        'product': product, 'similar_products': similar, 'seo_title': seo_title, 'parent_category': parent_category
    })

# --- РЕДИРЕКТ СТАРИХ ID -> SLUG ---
def redirect_old_product_urls(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return redirect('store:product_detail', slug=product.slug, permanent=True)

# --- ІНШІ ФУНКЦІЇ ---
def cart_detail_view(request): return render(request, 'store/cart.html', {'cart': Cart(request)})

@require_POST
def cart_add_view(request, product_id):
    cart = Cart(request); product = get_object_or_404(Product, id=product_id)
    cart.add(product=product, quantity=int(request.POST.get('quantity', 1)))
    return redirect(request.META.get('HTTP_REFERER', 'store:catalog'))

@require_POST
def cart_update_quantity_view(request, product_id):
    cart = Cart(request); product = get_object_or_404(Product, id=product_id)
    try:
        qty = int(request.POST.get('quantity', 1))
        if qty > product.stock_quantity: qty = product.stock_quantity
        if qty > 0: cart.add(product, qty, update_quantity=True)
        else: cart.remove(product)
    except: pass
    return redirect('store:cart_detail')

def cart_remove_view(request, product_id):
    cart = Cart(request); cart.remove(get_object_or_404(Product, id=product_id))
    return redirect('store:cart_detail')

# 🔥 ФУНКЦІЯ CHECKOUT (ДЕТАЛЬНЕ ЗАМОВЛЕННЯ В TELEGRAM) 🔥
def checkout_view(request):
    cart = Cart(request)
    if not cart: return redirect('store:catalog')
    
    if request.method == 'POST':
        shipping_type = request.POST.get('shipping_type')
        is_pickup = shipping_type == 'pickup'
        
        # Створюємо замовлення
        order = Order.objects.create(
            customer=request.user if request.user.is_authenticated else None,
            shipping_type=shipping_type,
            full_name=request.POST.get('pickup_name' if is_pickup else 'full_name'),
            phone=request.POST.get('pickup_phone' if is_pickup else 'phone'),
            email=None if is_pickup else request.POST.get('email'),
            city="Київ, Самовивіз" if is_pickup else request.POST.get('city'),
            nova_poshta_branch=None if is_pickup else request.POST.get('nova_poshta_branch')
        )

        # Формуємо список товарів для повідомлення
        items_text = ""
        for item in cart:
            p = item['product']
            # Зберігаємо в базу
            OrderItem.objects.create(order=order, product=p, quantity=item['quantity'], price_at_purchase=item['price'])
            # Додаємо в текст
            items_text += f"\n🔘 {p.brand.name} {p.name} ({p.width}/{p.profile} R{p.diameter}) — {item['quantity']} шт."

        # Формуємо інформацію про доставку
        delivery_info = "🏃 <b>САМОВИВІЗ</b> (Київ)"
        if not is_pickup:
            city = request.POST.get('city', '-')
            branch = request.POST.get('nova_poshta_branch', '-')
            delivery_info = f"🚚 <b>НОВА ПОШТА</b>\n📍 Місто: {city}\n🏢 Відділення: {branch}"

        # Збираємо повне повідомлення
        telegram_msg = (
            f"🔥 <b>НОВЕ ЗАМОВЛЕННЯ #{order.id}</b>\n"
            f"👤 {order.full_name}\n"
            f"📞 {order.phone}\n"
            f"------------------------------\n"
            f"{delivery_info}\n"
            f"------------------------------\n"
            f"🛒 <b>ТОВАРИ:</b>{items_text}\n"
            f"------------------------------\n"
            f"💰 <b>СУМА: {cart.get_total_price()} грн</b>"
        )
        
        send_telegram(telegram_msg)
        cart.clear()
        return redirect('users:profile' if request.user.is_authenticated else 'store:catalog')
        
    return render(request, 'store/checkout.html')

def about_view(request): return render(request, 'store/about.html')
def contacts_view(request): return render(request, 'store/contacts.html')
def delivery_payment_view(request): return render(request, 'store/delivery_payment.html')
def warranty_view(request): return render(request, 'store/warranty.html')

# 🔥 ФУНКЦІЯ ЧАТ-БОТА (SOS ЗАПИТ) 🔥
@require_POST
def bot_callback_view(request):
    try:
        data = json.loads(request.body)
        phone = data.get('phone')
        
        if phone:
            message = (
                f"🆘 <b>SOS ЗАПИТ (ЧАТ-БОТ)</b>\n"
                f"📞 Телефон: {phone}\n"
                f"⚠️ Клієнт просить допомоги з підбором!"
            )
            send_telegram(message)
            return JsonResponse({'status': 'ok'})
            
    except Exception as e:
        print(f"Bot Error: {e}")
    
    return JsonResponse({'status': 'error'}, status=400)

@transaction.atomic
def sync_google_sheet_view(request): return redirect('admin:store_product_changelist')
