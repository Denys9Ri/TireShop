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

from .models import Product, Order, OrderItem, Brand, SiteBanner

# --- CONFIG ---
SEASONS_MAP = {
    'zymovi': {'db': 'winter', 'ua': 'Зимові шини', 'adj': 'зимові'},
    'litni': {'db': 'summer', 'ua': 'Літні шини', 'adj': 'літні'},
    'vsesezonni': {'db': 'all_season', 'ua': 'Всесезонні шини', 'adj': 'всесезонні'}
}

# --- 🧠 ДОПОМІЖНІ ФУНКЦІЇ ---

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
    
    # Формування H1
    if season_info: parts.append(season_info['ua'])
    else: parts.append("Шини")
    
    if brand_obj: parts.append(brand_obj.name)
    
    size_str = ""
    if w and p and d:
        size_str = f"{w}/{p} R{d}"
        parts.append(size_str)
    
    h1 = " ".join(parts)
    
    # Формування Title (Комерційний)
    title = f"Купити {h1} — ціна від {min_price} грн | Київ, Україна | R16"
    
    # Формування Description
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
    """
    Генерує 'Хмару тегів' для перелінковки
    """
    links = []
    
    # 1. Якщо ми в Сезоні -> показати популярні розміри
    if current_season_slug and not w:
        top_sizes = [(175,70,13), (185,65,14), (195,65,15), (205,55,16), (215,60,16), (225,45,17), (235,55,18)]
        group = {'title': 'Популярні розміри:', 'items': []}
        for sw, sp, sd in top_sizes:
            url = reverse('store:seo_season_size', args=[current_season_slug, sw, sp, sd])
            group['items'].append({'text': f"R{sd} {sw}/{sp}", 'url': url})
        links.append(group)

    # 2. Якщо ми вибрали розмір -> показати ТОП бренди
    if w and p and d:
        # Шукаємо бренди, які є в цьому розмірі
        brands_qs = Brand.objects.filter(
            product__width=w, product__profile=p, product__diameter=d
        ).distinct()[:10]
        
        if brands_qs:
            group = {'title': 'Популярні бренди в цьому розмірі:', 'items': []}
            for b in brands_qs:
                # Якщо є сезон, лінкуємо на Бренд+Сезон+Розмір (Full), якщо ні - просто на Бренд
                try:
                    if current_season_slug:
                        url = reverse('store:seo_full', args=[b.name, current_season_slug, w, p, d])
                    else:
                        url = reverse('store:seo_brand', args=[b.name]) # Або інший фоллбек
                    group['items'].append({'text': b.name, 'url': url})
                except: pass
            links.append(group)
            
    # 3. Якщо ми в Бренді -> показати інші сезони
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

    # 1. Фільтр по бренду
    if brand_slug:
        brand_obj = Brand.objects.filter(name__iexact=brand_slug).first()
        if brand_obj: products = products.filter(brand=brand_obj)
        else: pass # 404 логіка тут

    # 2. Фільтр по сезону
    season_db = None
    if season_slug:
        if season_slug in SEASONS_MAP:
            season_db = SEASONS_MAP[season_slug]['db']
            products = products.filter(seasonality=season_db)
        else: raise Http404

    # 3. Фільтр по розміру
    if width and profile and diameter:
        products = products.filter(width=width, profile=profile, diameter=diameter)

    # 4. Аналітика (для сніпетів)
    stats = products.aggregate(min_price=Min('price'), count=Count('id'))
    min_price = stats['min_price'] if stats['min_price'] else 0
    prod_count = stats['count']

    # 5. Генерація всіх даних
    seo_data = generate_seo_meta(brand_obj, season_slug, width, profile, diameter, int(min_price))
    faq_schema = get_faq_schema(seo_data['h1'], int(min_price), prod_count)
    cross_links = get_cross_links(season_slug, brand_obj, width, profile, diameter)

    # 6. Стандартний контекст
    brands = Brand.objects.all().order_by('name')
    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'store/catalog.html', {
        'page_obj': page_obj, 'all_brands': brands,
        'all_widths': Product.objects.filter(width__gt=0).values_list('width', flat=True).distinct().order_by('width'),
        'all_profiles': Product.objects.filter(profile__gt=0).values_list('profile', flat=True).distinct().order_by('profile'),
        'all_diameters': Product.objects.filter(diameter__gt=0).values_list('diameter', flat=True).distinct().order_by('diameter'),
        'all_seasons': Product.SEASON_CHOICES,
        
        # Selected filters for UI
        'selected_brand_id': brand_obj.id if brand_obj else None,
        'selected_season': season_db,
        'selected_width': width, 'selected_profile': profile, 'selected_diameter': diameter,
        
        # SEO & RICH SNIPPETS
        'seo_title': seo_data['title'],
        'seo_h1': seo_data['h1'],
        'seo_description': seo_data['description'],
        'faq_schema': faq_schema,
        'cross_links': cross_links,
        'is_seo_page': True
    })

# --- ЗВИЧАЙНИЙ КАТАЛОГ (Для ?filter=...) ---
def catalog_view(request):
    products = get_base_products()
    # ... Тут код фільтрації (GET params) такий самий, як був раніше ...
    # Скорочено для економії місця. Він не змінюється.
    # Копіюємо з попереднього повідомлення повний вміст або залишаємо старий
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

    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
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
        'seo_title': "Каталог шин | R16.com.ua", 'seo_h1': "Всі шини"
    })

# --- PRODUCT DETAIL (SMART BREADCRUMBS) ---
def product_detail_view(request, slug):
    product = get_object_or_404(Product, slug=slug)
    similar = Product.objects.filter(width=product.width, profile=product.profile, diameter=product.diameter).exclude(id=product.id)[:4]
    seo_title = f"{product.brand.name} {product.name} {product.width}/{product.profile} R{product.diameter} - Купити | R16"
    
    # 🧠 Розумні хлібні крихти: ведемо на найглибшу можливу категорію
    parent_category = None
    season_slug = None
    for k, v in SEASONS_MAP.items():
        if v['db'] == product.seasonality:
            season_slug = k
            break
            
    if season_slug:
        # Спроба 1: Бренд + Сезон + Розмір
        try:
            url = reverse('store:seo_full', args=[product.brand.name, season_slug, product.width, product.profile, product.diameter])
            name = f"{SEASONS_MAP[season_slug]['ua']} {product.brand.name} {product.width}/{product.profile} R{product.diameter}"
            parent_category = {'name': name, 'url': url}
        except:
            # Спроба 2: Бренд + Сезон
            try:
                url = reverse('store:seo_brand_season', args=[product.brand.name, season_slug])
                name = f"{SEASONS_MAP[season_slug]['ua']} {product.brand.name}"
                parent_category = {'name': name, 'url': url}
            except:
                # Спроба 3: Просто сезон
                parent_category = {'name': SEASONS_MAP[season_slug]['ua'], 'url': reverse('store:seo_season', args=[season_slug])}

    return render(request, 'store/product_detail.html', {
        'product': product, 'similar_products': similar, 'seo_title': seo_title, 'parent_category': parent_category
    })

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
        for item in cart: OrderItem.objects.create(order=order, product=item['product'], quantity=item['quantity'], price_at_purchase=item['price'])
        send_telegram(f"🔥 <b>ЗАМОВЛЕННЯ #{order.id}</b>\n👤 {order.full_name}\n📞 {order.phone}")
        cart.clear()
        return redirect('users:profile' if request.user.is_authenticated else 'store:catalog')
    return render(request, 'store/checkout.html')
def about_view(request): return render(request, 'store/about.html')
def contacts_view(request): return render(request, 'store/contacts.html')
def delivery_payment_view(request): return render(request, 'store/delivery_payment.html')
def warranty_view(request): return render(request, 'store/warranty.html')
@require_POST
def bot_callback_view(request): return JsonResponse({'status': 'ok'})
@transaction.atomic
def sync_google_sheet_view(request): return redirect('admin:store_product_changelist')
