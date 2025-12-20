from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Case, When, Value, IntegerField, Min, Max, Count, Q
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

# --- ⚙️ КОНФІГУРАЦІЯ ---
SEASONS_MAP = {
    'zymovi': {'db': 'winter', 'ua': 'Зимові шини', 'adj': 'зимові'},
    'litni': {'db': 'summer', 'ua': 'Літні шини', 'adj': 'літні'},
    'vsesezonni': {'db': 'all_season', 'ua': 'Всесезонні шини', 'adj': 'всесезонні'}
}

# --- 🧠 SEO ШАБЛОНИ ---
SEO_TEMPLATES = {
    'winter': {
        'h2': "Чому варто купити зимові шини {brand} {size}?",
        'text': "<p>Зимова гума <b>{brand}</b> {size} розроблена для складних умов. Відмінне зчеплення на снігу та льоду.</p>",
        'faq_best': "Які зимові шини {brand} найкращі?",
        'faq_best_ans': "Найпопулярніші моделі {brand} забезпечують безпеку та короткий гальмівний шлях."
    },
    'summer': {
        'h2': "Літні шини {brand} {size}: Швидкість та контроль",
        'text': "<p>Літня гума <b>{brand}</b> {size} створена для динамічної їзди. Захист від аквапланування та комфорт.</p>",
        'faq_best': "Чи шумні літні шини {brand}?",
        'faq_best_ans': "Ні, лінійка {brand} вирізняється акустичним комфортом."
    },
    'all_season': {
        'h2': "Всесезонні шини {brand} {size}",
        'text': "<p>Універсальна гума <b>{brand}</b> {size} — компроміс для м'якої зими та літа.</p>",
        'faq_best': "Чи підходять для снігу?",
        'faq_best_ans': "Так, для легкого снігу. У сильну ожеледицю краще шипи."
    },
    'default': {
        'h2': "Купити шини {brand} {size} в Києві",
        'text': "<p>Інтернет-магазин R16 пропонує широкий вибір шин <b>{brand}</b> за низькими цінами.</p>",
        'faq_best': "Яка ціна?",
        'faq_best_ans': "Актуальну ціну дивіться в каталозі вище."
    }
}

# --- 🛠️ ДОПОМІЖНІ ФУНКЦІЇ ---
def send_telegram(message):
    try:
        token = settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_CHAT_ID
        if token and chat_id:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'})
    except: pass

def get_base_products():
    # Повертаємо всі товари, які мають розміри
    return Product.objects.filter(width__gt=0, diameter__gt=0).annotate(
        status_order=Case(When(stock_quantity__gt=0, then=Value(0)), default=Value(1), output_field=IntegerField())
    )

def generate_seo_content(brand_obj=None, season_db=None, w=None, p=None, d=None, min_price=0, max_price=0):
    brand_name = brand_obj.name if brand_obj else "Всі бренди"
    size_str = f"{w}/{p} R{d}" if (w and p and d) else ""
    
    key = season_db if season_db in SEO_TEMPLATES else 'default'
    template = SEO_TEMPLATES[key]

    h1_parts = []
    if season_db == 'winter': h1_parts.append("Зимові шини")
    elif season_db == 'summer': h1_parts.append("Літні шини")
    elif season_db == 'all_season': h1_parts.append("Всесезонні шини")
    else: h1_parts.append("Шини")
    
    if brand_obj: h1_parts.append(brand_obj.name)
    if size_str: h1_parts.append(size_str)
    
    h1_final = " ".join(h1_parts)
    title_final = f"{h1_final} — Ціна від {min_price} грн | R16.com.ua"
    
    try:
        description_html = template['text'].format(brand=brand_name, size=size_str)
        seo_h2 = template['h2'].format(brand=brand_name, size=size_str)
    except:
        description_html = SEO_TEMPLATES['default']['text'].format(brand=brand_name, size=size_str)
        seo_h2 = h1_final

    return {
        'title': title_final, 'h1': h1_final, 'seo_h2': seo_h2,
        'description_html': description_html,
        'meta_description': f"{h1_final} в наявності! 💰 Ціна: {min_price}-{max_price} грн.",
        'faq_key': key, 'brand_name': brand_name
    }

def get_faq_schema(seo_data, min_price):
    key = seo_data['faq_key']
    template = SEO_TEMPLATES[key]
    brand = seo_data['brand_name']
    
    try:
        q = template['faq_best'].format(brand=brand)
        a = template['faq_best_ans'].format(brand=brand)
    except:
        q = "Якість?"; a = "Відмінна."

    faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f"💰 Ціна?", "acceptedAnswer": {"@type": "Answer", "text": f"Від {min_price} грн."}},
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}},
            {"@type": "Question", "name": "🚚 Доставка?", "acceptedAnswer": {"@type": "Answer", "text": "Нова Пошта."}}
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
    return links

# --- 🔥 ГОЛОВНИЙ КОНТРОЛЕР (SEO + ПОШУК + ФІЛЬТРИ) 🔥 ---
def seo_matrix_view(request, slug=None, brand_slug=None, season_slug=None, width=None, profile=None, diameter=None):
    products = get_base_products()
    brand_obj = None
    season_db = None

    # 1. ОБРОБКА SEO URL (Clean URL)
    if slug:
        if slug in SEASONS_MAP: season_slug = slug
        else:
            brand_obj = Brand.objects.filter(name__iexact=slug).first()
            if brand_obj: brand_slug = slug

    # 2. 🔥 ОБРОБКА ПОШУКУ (TEXT SEARCH) 🔥
    query = request.GET.get('query', '').strip()
    if query:
        # Очищаємо запит від сміття (/, R, пробіли)
        clean = re.sub(r'[/\sR\-]', '', query, flags=re.IGNORECASE)
        # Перевіряємо, чи це розмір (наприклад 1956515)
        match = re.fullmatch(r'(\d{6,7})', clean)
        if match:
            d = match.group(1)
            # Якщо це розмір - шукаємо точно по розміру
            products = products.filter(width=int(d[:3]), profile=int(d[3:5]), diameter=int(d[5:]))
        else:
            # Якщо це текст - шукаємо в назві або бренді
            products = products.filter(Q(name__icontains=query) | Q(brand__name__icontains=query))

    # 3. 🔥 ОБРОБКА ФІЛЬТРІВ (DROPDOWN) 🔥
    # URL параметри мають пріоритет. Якщо їх немає - беремо з GET запиту
    
    # -- БРЕНД --
    if not brand_obj: # Якщо бренд не заданий в URL
        s_brand_id = request.GET.get('brand')
        if s_brand_id: 
            products = products.filter(brand__id=s_brand_id)
            brand_obj = Brand.objects.filter(id=s_brand_id).first()
    else:
        products = products.filter(brand=brand_obj)

    # -- СЕЗОН --
    if not season_slug: # Якщо сезон не заданий в URL
        s_season = request.GET.get('season')
        if s_season:
            products = products.filter(seasonality=s_season)
            # Спробуємо знайти назву сезону для SEO
            for k, v in SEASONS_MAP.items():
                if v['db'] == s_season:
                    season_slug = k
                    season_db = s_season
                    break
    elif season_slug in SEASONS_MAP:
        season_db = SEASONS_MAP[season_slug]['db']
        products = products.filter(seasonality=season_db)

    # -- РОЗМІРИ --
    req_width = width or request.GET.get('width')
    req_profile = profile or request.GET.get('profile')
    req_diameter = diameter or request.GET.get('diameter')

    if req_width: products = products.filter(width=req_width)
    if req_profile: products = products.filter(profile=req_profile)
    if req_diameter: products = products.filter(diameter=req_diameter)

    # --- СТАТИСТИКА (ДЛЯ SEO ТЕКСТІВ) ---
    stats = products.aggregate(min_price=Min('price'), max_price=Max('price'), count=Count('id'))
    min_price = stats['min_price'] if stats['min_price'] is not None else 0
    max_price = stats['max_price'] if stats['max_price'] is not None else 0

    # --- ГЕНЕРАЦІЯ SEO ---
    # Перетворюємо розміри в int для генератора
    w_int = int(req_width) if req_width else None
    p_int = int(req_profile) if req_profile else None
    d_int = int(req_diameter) if req_diameter else None

    seo_data = generate_seo_content(brand_obj, season_db, w_int, p_int, d_int, int(min_price), int(max_price))
    faq_schema = get_faq_schema(seo_data, int(min_price))
    cross_links = get_cross_links(season_slug, brand_obj, w_int, p_int, d_int)

    # --- СОРТУВАННЯ ---
    ordering = request.GET.get('ordering')
    if ordering == 'cheap': products = products.order_by('price')
    elif ordering == 'expensive': products = products.order_by('-price')
    else: products = products.order_by('status_order', 'brand__name', 'name') # Спочатку в наявності

    # --- UI ДАНІ ---
    brands = Brand.objects.all().order_by('name')
    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    # Зберігаємо параметри фільтру для пагінації (щоб при переході на стор. 2 фільтр не злітав)
    q_params = request.GET.copy()
    if 'page' in q_params: del q_params['page']

    return render(request, 'store/catalog.html', {
        'page_obj': page_obj, 
        'filter_query_string': q_params.urlencode(),
        'all_brands': brands,
        'all_widths': Product.objects.filter(width__gt=0).values_list('width', flat=True).distinct().order_by('width'),
        'all_profiles': Product.objects.filter(profile__gt=0).values_list('profile', flat=True).distinct().order_by('profile'),
        'all_diameters': Product.objects.filter(diameter__gt=0).values_list('diameter', flat=True).distinct().order_by('diameter'),
        'all_seasons': Product.SEASON_CHOICES,
        
        'selected_brand_id': brand_obj.id if brand_obj else (int(request.GET.get('brand')) if request.GET.get('brand') else None),
        'selected_season': season_db,
        'selected_width': w_int, 'selected_profile': p_int, 'selected_diameter': d_int,
        'search_query': query,
        
        'seo_title': seo_data['title'],
        'seo_h1': seo_data['h1'],
        'seo_h2': seo_data['seo_h2'],
        'seo_description': seo_data['meta_description'],
        'seo_text_html': seo_data['description_html'],
        'faq_schema': faq_schema,
        'cross_links': cross_links,
        'is_seo_page': True
    })

# --- ЗВИЧАЙНИЙ КАТАЛОГ ---
def catalog_view(request):
    return seo_matrix_view(request)

# --- ТОВАР ---
def product_detail_view(request, slug):
    product = get_object_or_404(Product, slug=slug)
    similar = Product.objects.filter(width=product.width, diameter=product.diameter).exclude(id=product.id)[:4]
    
    seo_data = generate_seo_content(product.brand, product.seasonality, product.width, product.profile, product.diameter, int(product.price), int(product.price))
    faq_schema = get_faq_schema(seo_data, int(product.price))

    parent_cat = None
    for k, v in SEASONS_MAP.items():
        if v['db'] == product.seasonality:
            parent_cat = {'name': v['ua'], 'url': reverse('store:seo_universal', args=[k])}
            break

    return render(request, 'store/product_detail.html', {
        'product': product, 'similar_products': similar, 'parent_category': parent_cat,
        'seo_title': seo_data['title'], 'seo_h1': seo_data['h1'], 'seo_h2': seo_data['seo_h2'],
        'seo_text_html': seo_data['description_html'], 'faq_schema': faq_schema
    })

def redirect_old_product_urls(request, product_id):
    p = get_object_or_404(Product, id=product_id)
    return redirect('store:product_detail', slug=p.slug, permanent=True)

# --- CART / INFO / CHECKOUT ---
def cart_detail_view(request): return render(request, 'store/cart.html', {'cart': Cart(request)})
@require_POST
def cart_add_view(request, product_id):
    cart = Cart(request); cart.add(get_object_or_404(Product, id=product_id), int(request.POST.get('quantity', 1)))
    return redirect(request.META.get('HTTP_REFERER', 'store:catalog'))
@require_POST
def cart_update_quantity_view(request, product_id):
    cart = Cart(request); cart.add(get_object_or_404(Product, id=product_id), int(request.POST.get('quantity', 1)), True)
    return redirect('store:cart_detail')
def cart_remove_view(request, product_id):
    cart = Cart(request); cart.remove(get_object_or_404(Product, id=product_id))
    return redirect('store:cart_detail')
# --- store/views.py (Оновлена функція замовлення) ---

def checkout_view(request):
    cart = Cart(request)
    if not cart: return redirect('store:catalog')
    
    if request.method == 'POST':
        # Отримуємо тип доставки (має бути 'pickup' або 'nova_poshta')
        shipping_type = request.POST.get('shipping_type', 'pickup') 
        is_pickup = (shipping_type == 'pickup')
        
        # Створюємо замовлення
        order = Order.objects.create(
            customer=request.user if request.user.is_authenticated else None,
            shipping_type=shipping_type,
            # Якщо самовивіз - беремо дані з полів для самовивозу, інакше - для доставки
            full_name=request.POST.get('pickup_name') if is_pickup else request.POST.get('full_name'),
            phone=request.POST.get('pickup_phone') if is_pickup else request.POST.get('phone'),
            email=None if is_pickup else request.POST.get('email'),
            city="Київ (Самовивіз)" if is_pickup else request.POST.get('city'),
            nova_poshta_branch="-" if is_pickup else request.POST.get('nova_poshta_branch')
        )

        # Зберігаємо товари
        items_text = ""
        for item in cart:
            p = item['product']
            OrderItem.objects.create(order=order, product=p, quantity=item['quantity'], price_at_purchase=item['price'])
            items_text += f"\n🔘 {p.brand.name} {p.name} ({p.width}/{p.profile} R{p.diameter}) — {item['quantity']} шт."

        # 🔥 ФОРМУВАННЯ ПОВІДОМЛЕННЯ ДЛЯ ТЕЛЕГРАМ 🔥
        if is_pickup:
            delivery_icon = "🏃"
            delivery_details = "САМОВИВІЗ (Київ, вул. Качали 3)"
        else:
            delivery_icon = "🚚"
            city = request.POST.get('city', 'Не вказано')
            branch = request.POST.get('nova_poshta_branch', 'Не вказано')
            delivery_details = f"НОВА ПОШТА\n📍 Місто: {city}\n🏢 Відділення: {branch}"

        telegram_msg = (
            f"🔥 <b>НОВЕ ЗАМОВЛЕННЯ #{order.id}</b>\n"
            f"👤 Клієнт: {order.full_name}\n"
            f"📞 Телефон: {order.phone}\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"{delivery_icon} {delivery_details}\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"🛒 <b>ТОВАРИ:</b>{items_text}\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"💰 <b>СУМА: {cart.get_total_price()} грн</b>"
        )
        
        send_telegram(telegram_msg)
        cart.clear()
        return redirect('store:catalog') # Або на сторінку "Дякуємо"
        
    return render(request, 'store/checkout.html')

def about_view(request): return render(request, 'store/about.html')
def contacts_view(request): return render(request, 'store/contacts.html')
def delivery_payment_view(request): return render(request, 'store/delivery_payment.html')
def warranty_view(request): return render(request, 'store/warranty.html')
@require_POST
def bot_callback_view(request):
    try:
        data = json.loads(request.body); phone = data.get('phone')
        if phone: send_telegram(f"🆘 SOS: {phone}"); return JsonResponse({'status': 'ok'})
    except: pass
    return JsonResponse({'status': 'err'})
def sync_google_sheet_view(request): return redirect('admin:store_product_changelist')
