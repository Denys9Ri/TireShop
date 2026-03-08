from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Case, When, Value, IntegerField, Min, Max, Count, Q
from django.conf import settings
from django.http import JsonResponse, Http404, HttpResponse
from django.db import transaction
from django.urls import reverse
from django.core.cache import cache
from django.contrib import messages
import json
import logging
import re
import requests

# Імпорти
from .cart import Cart
from .models import Product, Order, OrderItem, Brand, SiteBanner, AboutImage

# --- ⚙️ ЛОГЕР ---
logger = logging.getLogger(__name__)

# --- ⚙️ КОНФІГУРАЦІЯ ---

SEASONS_MAP = {
    'zimovi': {'db': 'winter', 'ua': 'Зимові шини', 'adj': 'зимові'},
    'zymovi': {'db': 'winter', 'ua': 'Зимові шини', 'adj': 'зимові'},
    'litni': {'db': 'summer', 'ua': 'Літні шини', 'adj': 'літні'},
    'vsesezonni': {'db': 'all-season', 'ua': 'Всесезонні шини', 'adj': 'всесезонні'},
}

DB_TO_SLUG_MAP = {
    'winter': 'zimovi',
    'summer': 'litni',
    'all-season': 'vsesezonni',
    'all_season': 'vsesezonni'
}

# --- 📚 FAQ DATA ---
FAQ_DATA = {
    'base': [
        ("Як дізнатися свій розмір шин?", "Подивись наклейку на дверях авто або на кришці бензобака — там буде щось типу 205/55 R16.<br>Не хочеш шукати — напиши нам марку, модель, рік і мотор, і ми підберемо."),
        ("Що означають цифри 205/55 R16?", "205 — ширина, 55 — висота профілю, R16 — діаметр диска. Це впливає на керованість і комфорт."),
        ("Що таке індекс навантаження і швидкості (напр. 91V)?", "Показує, скільки ваги і яку швидкість шина може витримати. Краще не ставити нижчі індекси, ніж радить виробник авто."),
        ("Можна купити дві шини замість чотирьох?", "Ідеально — чотири однакові. Якщо міняєш тільки дві, то кращу пару став на задню вісь — так авто буде більш стійким."),
        ("Який тиск качати в шинах?", "Дивись наклейку на авто. Не поради знайомих, а саме там. Неправильний тиск дає більший знос і гіршу керованість."),
        ("Що таке XL, RunFlat, C?", "<b>XL</b> — посилена, тримає більшу вагу.<br><b>RunFlat</b> — можна трохи їхати після проколу.<br><b>C</b> — для бусів або комерційного транспорту.<br>Якщо не впевнений — скажи авто, і підкажемо, чи це потрібно."),
        ("Як перевірити, наскільки свіжі шини?", "Є код DOT — тиждень і рік виробництва. Якщо треба, підкажемо перед покупкою."),
        ("Чому одна й та сама модель може коштувати по‑різному?", "Через індекси, посилення, RunFlat, партії, країну виробництва, наявність на складі."),
        ("Доставка й оплата — як це працює?", "Оформляєш замовлення, ми підтверджуємо наявність, відправляємо по Україні, підбираємо варіанти, якщо твій варіант відсутній."),
        ("Чи можна повернути шини?", "Так, якщо шини не були в користуванні і зберегли товарний вигляд. Умови пояснимо одразу.")
    ],
    'winter': [
        ("Коли переходити на зимову гуму?", "Коли температура стабільно опускається до приблизно +7°C і нижче. Це загальне правило, яке використовують виробники шин, бо при холоді літня гума гірше працює."),
        ("Шипи чи липучка — що кращe?", "<b>Шипи</b> — багато льоду, укатаний сніг, траси або села.<br><b>Липучка</b> — місто, мокрий асфальт, відлиги.<br>Скажи, де їздиш, і скажемо точніше."),
        ("Що означає "під шип"?", "Це модель, яку можна шипувати. Користь — якщо реально є лід чи частий сильний мороз."),
        ("Чи можна їздити взимку на дуже зношених шинах?", "Небезпечно. Взимку важливий протектор для гальмування і контролю. Краще міняти вчасно, ніж чекати до крайності.")
    ],
    'summer': [
        ("Коли ставити літню гуму?", "Коли температура стабільно вище приблизно +7°C. Літня гумa на теплій дорозі тримає краще."),
        ("Які літні шини кращі: для міста чи траси?", "<b>Місто</b> — тихі, зносостійкі.<br><b>Траса</b> — стабільні на швидкості, добре тримають дорогу у дощ.<br>Пиши, як їздиш, і підберемо."),
        ("Що таке аквапланування і як його уникнути?", "Це коли авто ніби пливе по воді і гірше керується. Допомагає: нормальний протектор, правильний тиск і адекватна швидкість у дощ.")
    ],
    'all_season': [
        ("Всесезонка — реально на весь рік?", "Так, але найкраще — якщо зима не дуже сувора. Якщо багато льоду чи заметів, краще окремо зимові."),
        ("Чим всесезонка гірша за літні чи зимові?", "Це компроміс: не дає максимуму ні в зимі, ні влітку, зате один комплект — зручно, менше замін."),
        ("Кому всесезонка підходить найбільше?", "Тим, хто їздить здебільшого містом, не дуже швидко й хоче мінімізувати сезонні заміни.")
    ]
}

# --- 🧠 SEO ШАБЛОНИ ---
SEO_TEMPLATES = {
    'winter': {'h2': "Чому варто купити зимові шини {brand} {size}?", 'text': "<p>Зимова гума <b>{brand}</b> {size} розроблена для складних умов.</p>"},
    'summer': {'h2': "Літні шини {brand} {size}: Швидкість та контроль", 'text': "<p>Літня гума <b>{brand}</b> {size} створена для динамічної їзди.</p>"},
    'all_season': {'h2': "Всесезонні шини {brand} {size}", 'text': "<p>Універсальна гума <b>{brand}</b> {size} — компроміс для м'якої зими.</p>"},
    'default': {'h2': "Купити шини {brand} {size} в Києві", 'text': "<p>Магазин R16 пропонує широкий вибір шин <b>{brand}</b>.</p>"}
}

# --- 🛡️ ВАЛІДАЦІЯ ТЕЛЕФОНУ ---
PHONE_REGEX = re.compile(r'^\+?[\d\s\-\(\)]{10,15}$')

def validate_phone(phone):
    """Повертає True якщо номер телефону валідний."""
    if not phone:
        return False
    digits_only = re.sub(r'[\s\-\(\)\+]', '', phone)
    return len(digits_only) >= 10 and PHONE_REGEX.match(phone)

# --- 🛠️ ДОПОМІЖНІ ФУНКЦІЇ ---
def send_telegram(message):
    """Відправляє повідомлення в Telegram. Логує помилку якщо не вдалося."""
    try:
        token = settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_CHAT_ID
        if not token or not chat_id:
            logger.warning("Telegram не налаштовано: TELEGRAM_BOT_TOKEN або TELEGRAM_CHAT_ID відсутні.")
            return
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'},
            timeout=5
        )
        if not response.ok:
            logger.error("Telegram API повернув помилку: %s", response.text)
    except requests.exceptions.Timeout:
        logger.error("Telegram: таймаут запиту.")
    except Exception as e:
        logger.error("Telegram: неочікувана помилка: %s", e)

def get_base_products():
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
    elif season_db == 'all-season': h1_parts.append("Всесезонні шини")
    else: h1_parts.append("Шини")

    if brand_obj: h1_parts.append(brand_obj.name)
    if size_str: h1_parts.append(size_str)

    h1_final = " ".join(h1_parts)
    title_final = f"{h1_final} — Ціна від {min_price} грн | R16.com.ua"
    description_html = f"<p>Великий вибір шин {brand_name} {size_str}. Низькі ціни, доставка по Україні.</p>"
    seo_h2 = f"Купити гуму {brand_name} {size_str}"

    return {
        'title': title_final, 'h1': h1_final, 'seo_h2': seo_h2,
        'description_html': description_html,
        'meta_description': f"{h1_final} в наявності! 🚚 Доставка по Україні. 💰 Ціна: {min_price}-{max_price} грн.",
        'faq_key': key, 'brand_name': brand_name
    }

def get_combined_faq(season_db):
    faq_list = FAQ_DATA['base'].copy()
    if season_db == 'winter': faq_list.extend(FAQ_DATA['winter'])
    elif season_db == 'summer': faq_list.extend(FAQ_DATA['summer'])
    elif season_db == 'all-season': faq_list.extend(FAQ_DATA['all_season'])
    return faq_list

def get_faq_schema_json(faq_list):
    schema_items = []
    for q, a in faq_list:
        clean_a = re.sub('<[^<]+?>', '', a)
        schema_items.append({"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": clean_a}})
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": schema_items}
    return json.dumps(faq)

def get_cross_links(current_season_slug, current_brand, w, p, d):
    cache_key = f"cross_links_{current_season_slug}_{current_brand}_{w}_{p}_{d}"
    cached_data = cache.get(cache_key)
    if cached_data: return cached_data
    return []

def robots_txt(request):
    lines = ["User-agent: *", "Disallow: /cart/", "Disallow: /checkout/", "Disallow: /admin/", "Allow: /", "Sitemap: https://r16.com.ua/sitemap.xml"]
    return HttpResponse("\n".join(lines), content_type="text/plain")

def home_view(request):
    featured_products = Product.objects.filter(stock_quantity__gt=4).order_by('-id')[:8]
    brands = Brand.objects.all().order_by('name')
    width_list = Product.objects.filter(width__gt=0).values_list('width', flat=True).distinct().order_by('width')
    profile_list = Product.objects.filter(profile__gt=0).values_list('profile', flat=True).distinct().order_by('profile')
    diameter_list = Product.objects.filter(diameter__gt=0).values_list('diameter', flat=True).distinct().order_by('diameter')

    return render(request, 'store/home.html', {
        'featured_products': featured_products,
        'brands': brands,
        'all_widths': width_list,
        'all_profiles': profile_list,
        'all_diameters': diameter_list,
        'all_seasons': Product.SEASON_CHOICES,
    })

def brand_landing_view(request, brand_slug):
    brand = Brand.objects.filter(Q(slug=brand_slug) | Q(name__iexact=brand_slug)).first()
    if not brand: raise Http404("Бренд не знайдено")

    products = Product.objects.filter(brand=brand, stock_quantity__gt=0).order_by('price')
    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    custom_page_range = page_obj.paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1)

    seo_data = generate_seo_content(brand, None, None, None, None, 0, 0)

    width_list = Product.objects.filter(width__gt=0).values_list('width', flat=True).distinct().order_by('width')
    profile_list = Product.objects.filter(profile__gt=0).values_list('profile', flat=True).distinct().order_by('profile')
    diameter_list = Product.objects.filter(diameter__gt=0).values_list('diameter', flat=True).distinct().order_by('diameter')

    return render(request, 'store/brand_detail.html', {
        'brand': brand, 'page_obj': page_obj, 'custom_page_range': custom_page_range,
        'seo_title': brand.seo_title or seo_data['title'],
        'seo_h1': brand.seo_h1 or seo_data['h1'],
        'meta_description': brand.description,
        'cross_links': [],
        'all_widths': width_list,
        'all_profiles': profile_list,
        'all_diameters': diameter_list,
    })

# --- 🔥 ГОЛОВНИЙ КОНТРОЛЕР ---
def seo_matrix_view(request, slug=None, brand_slug=None, season_slug=None, width=None, profile=None, diameter=None):

    req_season = request.GET.get('season')
    req_brand_id = request.GET.get('brand')
    req_width = width or request.GET.get('width')
    req_profile = profile or request.GET.get('profile')
    req_diameter = diameter or request.GET.get('diameter')

    if not any([slug, brand_slug, season_slug, width]) and (req_season or req_brand_id or (req_width and req_profile and req_diameter)):

        target_season_slug = None
        if req_season and req_season in DB_TO_SLUG_MAP:
            target_season_slug = DB_TO_SLUG_MAP[req_season]

        target_brand_slug = None
        if req_brand_id:
            try:
                b_obj = Brand.objects.filter(id=int(req_brand_id)).first()
                if b_obj: target_brand_slug = b_obj.slug
            except (ValueError, TypeError):
                pass

        has_size = bool(req_width and req_profile and req_diameter)

        if target_brand_slug and target_season_slug and has_size:
            return redirect('store:seo_full', brand_slug=target_brand_slug, season_slug=target_season_slug, width=req_width, profile=req_profile, diameter=req_diameter)
        elif target_brand_slug and has_size:
            return redirect('store:seo_brand_size', brand_slug=target_brand_slug, width=req_width, profile=req_profile, diameter=req_diameter)
        elif target_season_slug and has_size:
            return redirect('store:seo_season_size', season_slug=target_season_slug, width=req_width, profile=req_profile, diameter=req_diameter)
        elif target_brand_slug and target_season_slug:
            return redirect('store:seo_brand_season', brand_slug=target_brand_slug, season_slug=target_season_slug)
        elif has_size:
            return redirect('store:seo_size', width=req_width, profile=req_profile, diameter=req_diameter)
        elif target_season_slug and not req_width:
            return redirect('store:seo_universal', slug=target_season_slug)
        elif target_brand_slug:
            return redirect('store:brand_landing', brand_slug=target_brand_slug)

    products = get_base_products()
    brand_obj = None
    season_db = None

    if slug:
        if slug in SEASONS_MAP: season_slug = slug
        else:
            brand_obj = Brand.objects.filter(name__iexact=slug).first()
            if brand_obj: brand_slug = slug

    query = request.GET.get('query', '').strip()
    if query:
        clean = re.sub(r'[/\sR\-]', '', query, flags=re.IGNORECASE)
        match = re.fullmatch(r'(\d{6,7})', clean)
        if match:
            d = match.group(1)
            products = products.filter(width=int(d[:3]), profile=int(d[3:5]), diameter=int(d[5:]))
        else:
            products = products.filter(Q(name__icontains=query) | Q(brand__name__icontains=query))

    if brand_slug:
        products = products.filter(brand__slug=brand_slug)
        brand_obj = Brand.objects.filter(slug=brand_slug).first()
    elif req_brand_id:
        products = products.filter(brand__id=req_brand_id)
        brand_obj = Brand.objects.filter(id=req_brand_id).first()

    if req_season:
        products = products.filter(seasonality=req_season)
        season_db = req_season
        if req_season in DB_TO_SLUG_MAP:
            season_slug = DB_TO_SLUG_MAP[req_season]
    elif season_slug and season_slug in SEASONS_MAP:
        season_db = SEASONS_MAP[season_slug]['db']
        products = products.filter(seasonality=season_db)

    if req_width: products = products.filter(width=req_width)
    if req_profile: products = products.filter(profile=req_profile)
    if req_diameter: products = products.filter(diameter=req_diameter)

    real_products = products.filter(price__gt=0)
    if real_products.exists():
        stats = real_products.aggregate(min_price=Min('price'), max_price=Max('price'))
        min_price = stats['min_price']
        max_price = stats['max_price']
    else:
        min_price = 0
        max_price = 0

    w_int = int(req_width) if req_width else None
    p_int = int(req_profile) if req_profile else None
    d_int = int(req_diameter) if req_diameter else None

    seo_data = generate_seo_content(brand_obj, season_db, w_int, p_int, d_int, int(min_price), int(max_price))
    faq_list = get_combined_faq(season_db)
    faq_schema = get_faq_schema_json(faq_list)
    cross_links = get_cross_links(season_slug, brand_obj, w_int, p_int, d_int)

    ordering = request.GET.get('ordering')
    if ordering == 'cheap': products = products.filter(stock_quantity__gt=0).order_by('price')
    elif ordering == 'expensive': products = products.filter(stock_quantity__gt=0).order_by('-price')
    else: products = products.order_by('status_order', '-id')

    brands = Brand.objects.all().order_by('name')
    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    custom_page_range = page_obj.paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1)

    q_params = request.GET.copy()
    if 'page' in q_params: del q_params['page']

    return render(request, 'store/catalog.html', {
        'page_obj': page_obj, 'custom_page_range': custom_page_range,
        'filter_query_string': q_params.urlencode(),
        'all_brands': brands,
        'all_widths': Product.objects.filter(width__gt=0).values_list('width', flat=True).distinct().order_by('width'),
        'all_profiles': Product.objects.filter(profile__gt=0).values_list('profile', flat=True).distinct().order_by('profile'),
        'all_diameters': Product.objects.filter(diameter__gt=0).values_list('diameter', flat=True).distinct().order_by('diameter'),
        'all_seasons': Product.SEASON_CHOICES,
        'selected_brand_id': brand_obj.id if brand_obj else (int(req_brand_id) if req_brand_id else None),
        'selected_season': season_db,
        'selected_width': w_int, 'selected_profile': p_int, 'selected_diameter': d_int,
        'search_query': query,
        'seo_title': seo_data['title'], 'seo_h1': seo_data['h1'], 'seo_h2': seo_data['seo_h2'],
        'seo_description': seo_data['meta_description'], 'seo_text_html': seo_data['description_html'],
        'faq_schema': faq_schema, 'faq_list': faq_list, 'cross_links': cross_links, 'is_seo_page': True
    })

def catalog_view(request): return seo_matrix_view(request)

def product_detail_view(request, slug):
    product = get_object_or_404(Product, slug=slug)
    similar = Product.objects.filter(width=product.width, diameter=product.diameter).exclude(id=product.id)[:4]
    seo_data = generate_seo_content(product.brand, product.seasonality, product.width, product.profile, product.diameter, int(product.price), int(product.price))
    faq_list = get_combined_faq(product.seasonality)
    faq_schema = get_faq_schema_json(faq_list)
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

def cart_detail_view(request):
    return render(request, 'store/cart.html', {'cart': Cart(request)})

@require_POST
def cart_add_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1
    cart.add(product, quantity)
    return redirect(request.META.get('HTTP_REFERER', 'store:catalog'))

@require_POST
def cart_update_quantity_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    try:
        quantity = int(request.POST.get('quantity', 1))
        quantity = max(1, min(quantity, product.stock_quantity))
        cart.add(product, quantity, update_quantity=True)
    except (ValueError, TypeError):
        pass
    return redirect('store:cart_detail')

def cart_remove_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('store:cart_detail')

def cart_add_ajax_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    try:
        quantity_to_add = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity_to_add = 1

    cart_item = cart.cart.get(str(product.id))
    current_in_cart = cart_item['quantity'] if cart_item else 0
    total_wanted = current_in_cart + quantity_to_add

    # Не дозволяємо додати більше ніж є на складі
    if total_wanted > product.stock_quantity:
        quantity_to_add = product.stock_quantity - current_in_cart
        if quantity_to_add < 0:
            quantity_to_add = 0

    if quantity_to_add > 0:
        cart.add(product=product, quantity=quantity_to_add, update_quantity=False)

    html = render_to_string('store/includes/cart_offcanvas.html', {'cart': cart}, request=request)
    return JsonResponse({'html': html, 'cart_len': len(cart)})


# --- 🛒 CHECKOUT VIEW (ПОВНІСТЮ ПЕРЕПИСАНИЙ) ---
def checkout_view(request):
    cart = Cart(request)

    # Якщо кошик порожній — нема чого оформляти
    if not cart:
        return redirect('store:catalog')

    # Дані для попереднього заповнення форми
    def _get_prefill():
        data = {}
        if request.user.is_authenticated:
            data['email'] = request.user.email
            data['full_name'] = f"{request.user.first_name} {request.user.last_name}".strip()
            if hasattr(request.user, 'profile'):
                profile = request.user.profile
                data['phone'] = getattr(profile, 'phone_primary', '')
                data['city'] = getattr(profile, 'city', '')
                data['nova_poshta_branch'] = getattr(profile, 'nova_poshta_branch', '')
                if not data['full_name']:
                    data['full_name'] = getattr(profile, 'full_name', '')
        return data

    if request.method == 'POST':
        shipping_type = request.POST.get('shipping_type', 'pickup')
        is_pickup = (shipping_type == 'pickup')

        # --- СЕРВЕРНА ВАЛІДАЦІЯ ---
        errors = []

        if is_pickup:
            name = request.POST.get('pickup_name', '').strip()
            phone = request.POST.get('pickup_phone', '').strip()
            if not name:
                errors.append("Вкажіть ім'я та прізвище для самовивізу.")
            if not validate_phone(phone):
                errors.append("Вкажіть коректний номер телефону для самовивізу (мінімум 10 цифр).")
        else:
            name = request.POST.get('full_name', '').strip()
            phone = request.POST.get('phone', '').strip()
            city = request.POST.get('city', '').strip()
            branch = request.POST.get('nova_poshta_branch', '').strip()

            if not name:
                errors.append("Вкажіть прізвище та ім'я отримувача.")
            if not validate_phone(phone):
                errors.append("Вкажіть коректний номер телефону (мінімум 10 цифр).")
            if not city:
                errors.append("Вкажіть місто або село доставки.")
            if not branch:
                errors.append("Вкажіть номер відділення або поштомату.")

        # Якщо є помилки — повертаємо форму з повідомленнями та збереженими даними
        if errors:
            for error in errors:
                messages.error(request, error)
            # Повертаємо введені дані назад у форму
            user_data = {
                'full_name': request.POST.get('full_name') or request.POST.get('pickup_name', ''),
                'phone': request.POST.get('phone') or request.POST.get('pickup_phone', ''),
                'email': request.POST.get('email', ''),
                'city': request.POST.get('city', ''),
                'nova_poshta_branch': request.POST.get('nova_poshta_branch', ''),
            }
            return render(request, 'store/checkout.html', {'user_data': user_data})

        # --- СТВОРЕННЯ ЗАМОВЛЕННЯ ---
        with transaction.atomic():
            order = Order.objects.create(
                customer=request.user if request.user.is_authenticated else None,
                shipping_type=shipping_type,
                full_name=request.POST.get('pickup_name', '').strip() if is_pickup else name,
                phone=request.POST.get('pickup_phone', '').strip() if is_pickup else phone,
                email=None if is_pickup else request.POST.get('email', '').strip() or None,
                city="Київ (Самовивіз)" if is_pickup else request.POST.get('city', '').strip(),
                nova_poshta_branch="-" if is_pickup else request.POST.get('nova_poshta_branch', '').strip()
            )

            items_text = ""
            for item in cart:
                p = item['product']
                OrderItem.objects.create(
                    order=order,
                    product=p,
                    quantity=item['quantity'],
                    price_at_purchase=item['price']
                )
                items_text += f"\n🔘 {p.brand.name} {p.name} ({p.width}/{p.profile} R{p.diameter}) — {item['quantity']} шт."

        # --- TELEGRAM ---
        if is_pickup:
            delivery_icon = "🏃"
            delivery_details = "САМОВИВІЗ (Київ, вул. Качали 3)"
        else:
            delivery_icon = "🚚"
            city_val = request.POST.get('city', 'Не вказано')
            branch_val = request.POST.get('nova_poshta_branch', 'Не вказано')
            delivery_details = f"НОВА ПОШТА\n📍 Місто: {city_val}\n🏢 Відділення: {branch_val}"

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
        return redirect('store:catalog')

    # GET — показуємо форму
    return render(request, 'store/checkout.html', {'user_data': _get_prefill()})


def about_view(request):
    photos = AboutImage.objects.all().order_by('-created_at')
    return render(request, 'store/about.html', {'photos': photos})

def contacts_view(request):
    return render(request, 'store/contacts.html')

def delivery_payment_view(request):
    return render(request, 'store/delivery_payment.html')

def warranty_view(request):
    return render(request, 'store/warranty.html')

@require_POST
def bot_callback_view(request):
    try:
        data = json.loads(request.body)
        phone = data.get('phone', '').strip()
        if phone:
            send_telegram(f"🆘 SOS дзвінок: {phone}")
            return JsonResponse({'status': 'ok'})
        return JsonResponse({'status': 'err', 'message': 'Телефон не вказано'})
    except json.JSONDecodeError:
        logger.error("bot_callback_view: невалідний JSON")
        return JsonResponse({'status': 'err', 'message': 'Невалідний запит'})

def sync_google_sheet_view(request):
    return redirect('admin:store_product_changelist')

def faq_view(request):
    return render(request, 'store/faq.html')

def fix_product_names_view(request):
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Тільки для адміна'})

    batch_size = 300
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        page = 1

    start_index = (page - 1) * batch_size
    end_index = start_index + batch_size
    products = Product.objects.order_by('id')[start_index:end_index]

    if not products:
        return JsonResponse({'status': 'done', 'message': '🎉 Всі товари перевірено!'})

    count = 0
    log = []

    for p in products:
        raw_name = p.name
        clean_name = raw_name.replace("Шина", "").replace("шина", "")
        if p.brand:
            clean_name = re.sub(f"^{p.brand.name}", "", clean_name, flags=re.IGNORECASE)
            clean_name = re.sub(r'\(' + p.brand.name + r'\)', "", clean_name, flags=re.IGNORECASE)

        index_match = re.search(r'\b(\d{2,3}[A-Z]{1,2})\b', clean_name)
        load_speed_idx = index_match.group(1) if index_match else ""

        clean_name_no_size = re.sub(r'\d{3}/\d{2}[R|Z]\d{2}', '', clean_name)
        if load_speed_idx:
            clean_name_no_size = clean_name_no_size.replace(load_speed_idx, "")

        model_name = re.sub(r'^\W+|\W+$', '', clean_name_no_size.strip())
        final_name = f"{model_name} {load_speed_idx}".strip() if load_speed_idx else model_name
        final_name = re.sub(r'\s+', ' ', final_name).strip()

        if final_name != p.name and len(final_name) > 1:
            log.append(f"{p.id}: {p.name} -> {final_name}")
            # Використовуємо update() щоб уникнути перерахунку ціни через save()
            Product.objects.filter(pk=p.pk).update(name=final_name)
            count += 1

    next_page = page + 1
    next_link = f"{request.path}?page={next_page}"
    return JsonResponse({
        'status': 'processing',
        'current_page': page,
        'fixed_in_this_batch': count,
        'NEXT_STEP': f"Перейдіть сюди: {next_link}",
        'log': log[:20]
    })


def sitemap_xml_view(request):
    """Генерує динамічну карту сайту з усіма SEO-посиланнями."""
    base_url = "https://r16.com.ua"
    urls = []

    # 1. Статичні сторінки
    static_names = ['store:home', 'store:catalog', 'store:about', 'store:contacts',
                    'store:delivery_payment', 'store:warranty', 'store:faq']
    for name in static_names:
        try:
            urls.append({'loc': f"{base_url}{reverse(name)}", 'priority': '0.5', 'freq': 'daily'})
        except Exception:
            pass

    # 2. Бренди
    for brand in Brand.objects.exclude(slug__isnull=True).exclude(slug=''):
        urls.append({'loc': f"{base_url}/shiny/brendy/{brand.slug}/", 'priority': '0.7', 'freq': 'weekly'})

    # 3. Товари
    for product in Product.objects.exclude(slug__isnull=True).exclude(slug=''):
        urls.append({'loc': f"{base_url}/product/{product.slug}/", 'priority': '0.8', 'freq': 'weekly'})

    # 4. SEO матриця — розміри де є хоч 1 шина
    sizes = Product.objects.filter(stock_quantity__gt=0).values('width', 'profile', 'diameter').distinct()
    for s in sizes:
        w, p, d = s['width'], s['profile'], s['diameter']
        urls.append({'loc': f"{base_url}/shiny/{w}-{p}-r{d}/", 'priority': '0.9', 'freq': 'daily'})
        for seas in ['zimovi', 'litni', 'vsesezonni']:
            urls.append({'loc': f"{base_url}/shiny/{seas}/{w}-{p}-r{d}/", 'priority': '0.9', 'freq': 'daily'})

    # 5. Загальні сезони
    for seas in ['zimovi', 'litni', 'vsesezonni']:
        urls.append({'loc': f"{base_url}/shiny/{seas}/", 'priority': '0.8', 'freq': 'daily'})

    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        xml_content += f"  <url>\n    <loc>{u['loc']}</loc>\n    <changefreq>{u['freq']}</changefreq>\n    <priority>{u['priority']}</priority>\n  </url>\n"
    xml_content += '</urlset>'

    return HttpResponse(xml_content, content_type="application/xml")
