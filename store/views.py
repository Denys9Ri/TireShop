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
import requests
import re
import logging

logger = logging.getLogger(__name__)

from .cart import Cart
from .models import Product, Order, OrderItem, Brand, SiteBanner, AboutImage

# --- ⚙️ КОНФІГУРАЦІЯ ---

SEASONS_MAP = {
    'zimovi':     {'db': 'winter',     'ua': 'Зимові шини',     'adj': 'зимові'},
    'zymovi':     {'db': 'winter',     'ua': 'Зимові шини',     'adj': 'зимові'},
    'litni':      {'db': 'summer',     'ua': 'Літні шини',      'adj': 'літні'},
    'vsesezonni': {'db': 'all-season', 'ua': 'Всесезонні шини', 'adj': 'всесезонні'},
}

DB_TO_SLUG_MAP = {
    'winter':     'zimovi',
    'summer':     'litni',
    'all-season': 'vsesezonni',
    'all_season': 'vsesezonni',
}

# --- 📚 FAQ DATA ---
FAQ_DATA = {
    'base': [
        ("Як дізнатися свій розмір шин?",
         "Подивись наклейку на дверях авто або на кришці бензобака — там буде щось типу 205/55 R16.<br>"
         "Не хочеш шукати — напиши нам марку, модель, рік і мотор, і ми підберемо."),
        ("Що означають цифри 205/55 R16?",
         "205 — ширина, 55 — висота профілю, R16 — діаметр диска. Це впливає на керованість і комфорт."),
        ("Що таке індекс навантаження і швидкості (напр. 91V)?",
         "Показує, скільки ваги і яку швидкість шина може витримати. Краще не ставити нижчі індекси, ніж радить виробник авто."),
        ("Можна купити дві шини замість чотирьох?",
         "Ідеально — чотири однакові. Якщо міняєш тільки дві, то кращу пару став на задню вісь — так авто буде більш стійким."),
        ("Який тиск качати в шинах?",
         "Дивись наклейку на авто. Не поради знайомих, а саме там. Неправильний тиск дає більший знос і гіршу керованість."),
        ("Що таке XL, RunFlat, C?",
         "<b>XL</b> — посилена, тримає більшу вагу.<br><b>RunFlat</b> — можна трохи їхати після проколу.<br>"
         "<b>C</b> — для бусів або комерційного транспорту.<br>Якщо не впевнений — скажи авто, і підкажемо, чи це потрібно."),
        ("Як перевірити, наскільки свіжі шини?",
         "Є код DOT — тиждень і рік виробництва. Якщо треба, підкажемо перед покупкою."),
        ("Чому одна й та сама модель може коштувати по-різному?",
         "Через індекси, посилення, RunFlat, партії, країну виробництва, наявність на складі."),
        ("Доставка й оплата — як це працює?",
         "Оформляєш замовлення, ми підтверджуємо наявність, відправляємо по Україні Новою Поштою. "
         "Підберемо варіанти, якщо твій розмір тимчасово відсутній."),
        ("Чи можна повернути шини?",
         "Так, якщо шини не були в користуванні і зберегли товарний вигляд. Умови пояснимо одразу."),
    ],
    'winter': [
        ("Коли переходити на зимову гуму?",
         "Коли температура стабільно опускається до +7°C і нижче. При холоді літня гума гірше працює."),
        ("Шипи чи липучка — що краще?",
         "<b>Шипи</b> — багато льоду, укатаний сніг, траси або села.<br>"
         "<b>Липучка</b> — місто, мокрий асфальт, відлиги.<br>Скажи, де їздиш, і скажемо точніше."),
        ('Що означає "під шип"?',
         "Це модель, яку можна шипувати. Користь — якщо реально є лід чи частий сильний мороз."),
        ("Чи можна їздити взимку на дуже зношених шинах?",
         "Небезпечно. Взимку важливий протектор для гальмування і контролю. Краще міняти вчасно."),
    ],
    'summer': [
        ("Коли ставити літню гуму?",
         "Коли температура стабільно вище +7°C. Літня гума на теплій дорозі тримає краще."),
        ("Які літні шини кращі: для міста чи траси?",
         "<b>Місто</b> — тихі, зносостійкі.<br><b>Траса</b> — стабільні на швидкості, добре тримають дорогу у дощ.<br>"
         "Пиши, як їздиш, і підберемо."),
        ("Що таке аквапланування і як його уникнути?",
         "Це коли авто ніби пливе по воді і гірше керується. Допомагає: нормальний протектор, "
         "правильний тиск і адекватна швидкість у дощ."),
    ],
    'all_season': [
        ("Всесезонка — реально на весь рік?",
         "Так, але найкраще — якщо зима не дуже сувора. Якщо багато льоду чи заметів, краще окремо зимові."),
        ("Чим всесезонка гірша за літні чи зимові?",
         "Це компроміс: не дає максимуму ні взимку, ні влітку, зате один комплект — зручно, менше замін."),
        ("Кому всесезонка підходить найбільше?",
         "Тим, хто їздить здебільшого містом, не дуже швидко й хоче мінімізувати сезонні заміни."),
    ],
}

# --- 🧠 SEO ШАБЛОНИ ---
SEO_TEMPLATES = {
    'winter': {
        'h2': 'Чому варто купити зимові шини {brand} {size}?',
        'text': (
            '<p>Зимові шини <b>{brand}</b> {size} розроблені для складних умов — льоду, снігу та слякоті. '
            'Спеціальний склад гуми залишається м\'яким при низьких температурах, забезпечуючи надійне зчеплення '
            'і коротший гальмівний шлях. Купуйте зимові шини заздалегідь, до початку сезону.</p>'
        ),
    },
    'summer': {
        'h2': 'Літні шини {brand} {size}: швидкість та контроль',
        'text': (
            '<p>Літні шини <b>{brand}</b> {size} розроблені для їзди при температурі вище +7°C. '
            'Жорсткіший склад гуми забезпечує точну керованість, короткий гальмівний шлях на сухому і мокрому '
            'асфальті та економію палива. Ідеальні для міста і трас.</p>'
        ),
    },
    'all_season': {
        'h2': 'Всесезонні шини {brand} {size} — один комплект на весь рік',
        'text': (
            '<p>Всесезонні шини <b>{brand}</b> {size} — універсальне рішення для регіонів з м\'якою зимою. '
            'Поєднують властивості літніх і зимових шин: прийнятна поведінка в дощ, на снігу та суху погоду. '
            'Підходять для міської їзди без необхідності в сезонній заміні.</p>'
        ),
    },
    'default': {
        'h2': 'Купити шини {brand} {size} в Києві',
        'text': (
            '<p>Магазин R16.com.ua пропонує широкий вибір шин <b>{brand}</b> {size}. '
            'Актуальний залишок на складі, швидка відправка Новою Поштою по всій Україні. '
            'Самовивіз у Києві — безкоштовно.</p>'
        ),
    },
}


# --- 🛠️ ДОПОМІЖНІ ФУНКЦІЇ ---

def send_telegram(message):
    try:
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', None)
        if not token or not chat_id:
            logger.warning("Telegram credentials not configured")
            return
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'},
            timeout=5,
        )
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        logger.error("Telegram request timed out")
    except Exception as e:
        logger.error(f"Telegram send error: {e}")


def get_base_products():
    return Product.objects.filter(width__gt=0, diameter__gt=0).annotate(
        status_order=Case(
            When(stock_quantity__gt=0, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    )


def generate_seo_content(brand_obj=None, season_db=None, w=None, p=None, d=None,
                          min_price=0, max_price=0):
    brand_name = brand_obj.name if brand_obj else ""
    size_str = f"{w}/{p} R{d}" if (w and p and d) else ""

    # H1 — завжди з "Купити" для кращого CTR
    h1_parts = []
    if season_db == 'winter':
        h1_parts.append("Купити зимові шини")
    elif season_db == 'summer':
        h1_parts.append("Купити літні шини")
    elif season_db == 'all-season':
        h1_parts.append("Купити всесезонні шини")
    else:
        h1_parts.append("Купити шини")

    if brand_obj:
        h1_parts.append(brand_obj.name)
    if size_str:
        h1_parts.append(size_str)

    h1_final = " ".join(h1_parts)

    # Title — з ціною якщо є (підвищує CTR на ~15%)
    if min_price and min_price > 0:
        title_final = f"{h1_final} — ціна від {min_price} грн | R16.com.ua"
    else:
        title_final = f"{h1_final} | R16.com.ua"

    # Meta description — з ціновим діапазоном і CTA
    if min_price and max_price and min_price > 0:
        price_str = f"Ціна: {min_price}–{max_price} грн."
    elif min_price and min_price > 0:
        price_str = f"Ціна від {min_price} грн."
    else:
        price_str = ""

    meta_description = (
        f"{h1_final} в наявності. {price_str} "
        f"🚚 Доставка Новою Поштою по Україні. 📍 Самовивіз у Києві. Гарантія якості."
    ).strip()

    # SEO H2 та текст
    key = 'default'
    if season_db == 'winter':
        key = 'winter'
    elif season_db == 'summer':
        key = 'summer'
    elif season_db in ('all-season', 'all_season'):
        key = 'all_season'

    template = SEO_TEMPLATES[key]
    fmt = {'brand': brand_name or "R16", 'size': size_str}
    seo_h2 = template['h2'].format(**fmt)
    description_html = template['text'].format(**fmt)

    # Canonical URL — без page=, зі збереженням фільтрів (вирішує дублі)
    canonical_params = []
    if w:         canonical_params.append(f"width={w}")
    if p:         canonical_params.append(f"profile={p}")
    if d:         canonical_params.append(f"diameter={d}")
    if season_db: canonical_params.append(f"season={season_db}")
    if brand_obj: canonical_params.append(f"brand={brand_obj.id}")

    canonical_qs = "&".join(canonical_params)
    canonical_url = (
        f"https://r16.com.ua/catalog/?{canonical_qs}"
        if canonical_qs
        else "https://r16.com.ua/catalog/"
    )

    return {
        'title': title_final,
        'h1': h1_final,
        'seo_h2': seo_h2,
        'description_html': description_html,
        'meta_description': meta_description,
        'faq_key': key,
        'brand_name': brand_name,
        'canonical_url': canonical_url,
    }


def get_combined_faq(season_db):
    faq_list = FAQ_DATA['base'].copy()
    if season_db == 'winter':
        faq_list.extend(FAQ_DATA['winter'])
    elif season_db == 'summer':
        faq_list.extend(FAQ_DATA['summer'])
    elif season_db in ('all-season', 'all_season'):
        faq_list.extend(FAQ_DATA['all_season'])
    return faq_list


def get_faq_schema_json(faq_list):
    schema_items = []
    for q, a in faq_list:
        clean_a = re.sub('<[^<]+?>', '', a)
        schema_items.append({
            "@type": "Question",
            "name": q,
            "acceptedAnswer": {"@type": "Answer", "text": clean_a},
        })
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": schema_items,
    }, ensure_ascii=False)


def get_cross_links(current_season_slug, current_brand, w, p, d):
    """Генерує перехресні посилання для внутрішньої перелінковки."""
    cache_key = f"cross_links_{current_season_slug}_{current_brand}_{w}_{p}_{d}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    links = []

    # Посилання на інші сезони того ж розміру
    if w and p and d:
        season_items = []
        for slug, info in SEASONS_MAP.items():
            if slug == 'zymovi':
                continue
            if current_season_slug and slug == current_season_slug:
                continue
            season_items.append({
                'url': f"/catalog/?width={w}&profile={p}&diameter={d}&season={info['db']}",
                'text': f"{info['ua']} {w}/{p} R{d}",
            })
        if season_items:
            links.append({'title': 'Цей розмір за сезоном', 'items': season_items})

    # Посилання на суміжні діаметри
    if w and p and d:
        nearby = []
        for diam in [int(d) - 1, int(d) + 1]:
            if 13 <= diam <= 22:
                nearby.append({
                    'url': f"/catalog/?width={w}&profile={p}&diameter={diam}",
                    'text': f"Шини {w}/{p} R{diam}",
                })
        if nearby:
            links.append({'title': 'Схожі розміри', 'items': nearby})

    cache.set(cache_key, links, 60 * 60)
    return links


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /cart/",
        "Disallow: /checkout/",
        "Disallow: /admin/",
        "Allow: /",
        "Sitemap: https://r16.com.ua/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


# --- 👁️ VIEWS ---

def home_view(request):
    featured_products = Product.objects.filter(stock_quantity__gt=4).order_by('-id')[:8]
    brands = Brand.objects.all().order_by('name')
    width_list = (Product.objects.filter(width__gt=0)
                  .values_list('width', flat=True).distinct().order_by('width'))
    profile_list = (Product.objects.filter(profile__gt=0)
                    .values_list('profile', flat=True).distinct().order_by('profile'))
    diameter_list = (Product.objects.filter(diameter__gt=0)
                     .values_list('diameter', flat=True).distinct().order_by('diameter'))
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
    if not brand:
        raise Http404("Бренд не знайдено")

    products = Product.objects.filter(brand=brand, stock_quantity__gt=0).order_by('price')
    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    custom_page_range = page_obj.paginator.get_elided_page_range(
        page_obj.number, on_each_side=2, on_ends=1
    )
    stats = products.aggregate(min_price=Min('price'), max_price=Max('price'))
    seo_data = generate_seo_content(
        brand, None, None, None, None,
        int(stats['min_price'] or 0), int(stats['max_price'] or 0),
    )
    faq_list = get_combined_faq(None)
    faq_schema = get_faq_schema_json(faq_list)

    width_list = (Product.objects.filter(width__gt=0)
                  .values_list('width', flat=True).distinct().order_by('width'))
    profile_list = (Product.objects.filter(profile__gt=0)
                    .values_list('profile', flat=True).distinct().order_by('profile'))
    diameter_list = (Product.objects.filter(diameter__gt=0)
                     .values_list('diameter', flat=True).distinct().order_by('diameter'))

    return render(request, 'store/brand_detail.html', {
        'brand': brand,
        'page_obj': page_obj,
        'custom_page_range': custom_page_range,
        'seo_title': brand.seo_title or seo_data['title'],
        'seo_h1': brand.seo_h1 or seo_data['h1'],
        'seo_description': brand.description or seo_data['meta_description'],
        'faq_schema': faq_schema,
        'faq_list': faq_list,
        'cross_links': [],
        'all_widths': width_list,
        'all_profiles': profile_list,
        'all_diameters': diameter_list,
        'canonical_url': seo_data['canonical_url'],
    })


def seo_matrix_view(request, slug=None, brand_slug=None, season_slug=None,
                    width=None, profile=None, diameter=None):
    req_season   = request.GET.get('season')
    req_brand_id = request.GET.get('brand')
    req_width    = width    or request.GET.get('width')
    req_profile  = profile  or request.GET.get('profile')
    req_diameter = diameter or request.GET.get('diameter')

    # Редіректи GET → SEO-URL
    if not any([slug, brand_slug, season_slug, width]) and (
        req_season or req_brand_id or (req_width and req_profile and req_diameter)
    ):
        target_season_slug = DB_TO_SLUG_MAP.get(req_season) if req_season else None

        target_brand_slug = None
        if req_brand_id:
            try:
                b_obj = Brand.objects.filter(id=int(req_brand_id)).first()
                if b_obj:
                    target_brand_slug = b_obj.slug
            except (ValueError, TypeError):
                pass

        has_size = bool(req_width and req_profile and req_diameter)

        if target_brand_slug and target_season_slug and has_size:
            return redirect('store:seo_full', brand_slug=target_brand_slug,
                            season_slug=target_season_slug,
                            width=req_width, profile=req_profile, diameter=req_diameter)
        elif target_brand_slug and has_size:
            return redirect('store:seo_brand_size', brand_slug=target_brand_slug,
                            width=req_width, profile=req_profile, diameter=req_diameter)
        elif target_season_slug and has_size:
            return redirect('store:seo_season_size', season_slug=target_season_slug,
                            width=req_width, profile=req_profile, diameter=req_diameter)
        elif target_brand_slug and target_season_slug:
            return redirect('store:seo_brand_season',
                            brand_slug=target_brand_slug, season_slug=target_season_slug)
        elif has_size:
            return redirect('store:seo_size',
                            width=req_width, profile=req_profile, diameter=req_diameter)
        elif target_season_slug and not req_width:
            return redirect('store:seo_universal', slug=target_season_slug)
        elif target_brand_slug:
            return redirect('store:brand_landing', brand_slug=target_brand_slug)

    # Фільтрація товарів
    products = get_base_products()
    brand_obj = None
    season_db = None

    if slug:
        if slug in SEASONS_MAP:
            season_slug = slug
        else:
            brand_obj = Brand.objects.filter(name__iexact=slug).first()
            if brand_obj:
                brand_slug = slug

    query = request.GET.get('query', '').strip()
    if query:
        clean = re.sub(r'[/\sR\-]', '', query, flags=re.IGNORECASE)
        match = re.fullmatch(r'(\d{6,7})', clean)
        if match:
            dg = match.group(1)
            products = products.filter(
                width=int(dg[:3]), profile=int(dg[3:5]), diameter=int(dg[5:])
            )
        else:
            products = products.filter(
                Q(name__icontains=query) | Q(brand__name__icontains=query)
            )

    if brand_slug:
        products = products.filter(brand__slug=brand_slug)
        brand_obj = Brand.objects.filter(slug=brand_slug).first()
    elif req_brand_id:
        try:
            products = products.filter(brand__id=int(req_brand_id))
            brand_obj = Brand.objects.filter(id=int(req_brand_id)).first()
        except (ValueError, TypeError):
            pass

    if req_season:
        products = products.filter(seasonality=req_season)
        season_db = req_season
        season_slug = DB_TO_SLUG_MAP.get(req_season)
    elif season_slug and season_slug in SEASONS_MAP:
        season_db = SEASONS_MAP[season_slug]['db']
        products = products.filter(seasonality=season_db)

    for val, attr in [(req_width, 'width'), (req_profile, 'profile'), (req_diameter, 'diameter')]:
        if val:
            try:
                products = products.filter(**{attr: int(val)})
            except (ValueError, TypeError):
                pass

    real_products = products.filter(price__gt=0)
    if real_products.exists():
        stats = real_products.aggregate(min_price=Min('price'), max_price=Max('price'))
        min_price = int(stats['min_price'] or 0)
        max_price = int(stats['max_price'] or 0)
    else:
        min_price = max_price = 0

    w_int = int(req_width)    if req_width    else None
    p_int = int(req_profile)  if req_profile  else None
    d_int = int(req_diameter) if req_diameter else None

    seo_data    = generate_seo_content(brand_obj, season_db, w_int, p_int, d_int, min_price, max_price)
    faq_list    = get_combined_faq(season_db)
    faq_schema  = get_faq_schema_json(faq_list)
    cross_links = get_cross_links(season_slug, brand_obj, w_int, p_int, d_int)

    ordering = request.GET.get('ordering')
    if ordering == 'cheap':
        products = products.filter(stock_quantity__gt=0).order_by('price')
    elif ordering == 'expensive':
        products = products.filter(stock_quantity__gt=0).order_by('-price')
    else:
        products = products.order_by('status_order', '-id')

    brands = Brand.objects.all().order_by('name')
    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    custom_page_range = page_obj.paginator.get_elided_page_range(
        page_obj.number, on_each_side=2, on_ends=1
    )

    q_params = request.GET.copy()
    q_params.pop('page', None)

    return render(request, 'store/catalog.html', {
        'page_obj': page_obj,
        'custom_page_range': custom_page_range,
        'filter_query_string': q_params.urlencode(),
        'all_brands': brands,
        'all_widths': (Product.objects.filter(width__gt=0)
                       .values_list('width', flat=True).distinct().order_by('width')),
        'all_profiles': (Product.objects.filter(profile__gt=0)
                         .values_list('profile', flat=True).distinct().order_by('profile')),
        'all_diameters': (Product.objects.filter(diameter__gt=0)
                          .values_list('diameter', flat=True).distinct().order_by('diameter')),
        'all_seasons': Product.SEASON_CHOICES,
        'selected_brand_id': brand_obj.id if brand_obj else (
            int(req_brand_id) if req_brand_id else None
        ),
        'selected_season':   season_db,
        'selected_width':    w_int,
        'selected_profile':  p_int,
        'selected_diameter': d_int,
        'search_query': query,
        'seo_title':       seo_data['title'],
        'seo_h1':          seo_data['h1'],
        'seo_h2':          seo_data['seo_h2'],
        'seo_description': seo_data['meta_description'],
        'seo_text_html':   seo_data['description_html'],
        'faq_schema':      faq_schema,
        'faq_list':        faq_list,
        'cross_links':     cross_links,
        'canonical_url':   seo_data['canonical_url'],
        'is_seo_page': True,
    })


def catalog_view(request):
    return seo_matrix_view(request)


def product_detail_view(request, slug):
    product = get_object_or_404(Product, slug=slug)
    similar = Product.objects.filter(
        width=product.width, diameter=product.diameter
    ).exclude(id=product.id)[:4]

    seo_data = generate_seo_content(
        product.brand, product.seasonality,
        product.width, product.profile, product.diameter,
        int(product.price), int(product.price),
    )
    faq_list   = get_combined_faq(product.seasonality)
    faq_schema = get_faq_schema_json(faq_list)

    parent_cat = None
    for k, v in SEASONS_MAP.items():
        if v['db'] == product.seasonality and k != 'zymovi':
            parent_cat = {
                'name': v['ua'],
                'url': reverse('store:seo_universal', args=[k]),
            }
            break

    return render(request, 'store/product_detail.html', {
        'product': product,
        'similar_products': similar,
        'parent_category': parent_cat,
        'seo_title':     seo_data['title'],
        'seo_h1':        seo_data['h1'],
        'seo_h2':        seo_data['seo_h2'],
        'seo_text_html': seo_data['description_html'],
        'faq_schema':    faq_schema,
        'faq_list':      faq_list,
    })


def redirect_old_product_urls(request, product_id):
    p = get_object_or_404(Product, id=product_id)
    return redirect('store:product_detail', slug=p.slug, permanent=True)


def cart_detail_view(request):
    return render(request, 'store/cart.html', {'cart': Cart(request)})


@require_POST
def cart_add_view(request, product_id):
    cart = Cart(request)
    cart.add(get_object_or_404(Product, id=product_id), int(request.POST.get('quantity', 1)))
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
    cart.remove(get_object_or_404(Product, id=product_id))
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
    if total_wanted > product.stock_quantity:
        quantity_to_add = max(0, product.stock_quantity - current_in_cart)
    if quantity_to_add > 0:
        cart.add(product=product, quantity=quantity_to_add, update_quantity=False)

    html = render_to_string(
        'store/includes/cart_offcanvas.html', {'cart': cart}, request=request
    )
    return JsonResponse({'html': html, 'cart_len': len(cart)})


def checkout_view(request):
    cart = Cart(request)
    if not cart:
        return redirect('store:catalog')

    if request.method == 'POST':
        shipping_type = request.POST.get('shipping_type', 'pickup')
        is_pickup = (shipping_type == 'pickup')

        raw_name   = request.POST.get('pickup_name') if is_pickup else request.POST.get('full_name')
        raw_phone  = request.POST.get('pickup_phone') if is_pickup else request.POST.get('phone')
        raw_city   = "Київ (Самовивіз)" if is_pickup else request.POST.get('city')
        raw_branch = "-" if is_pickup else request.POST.get('nova_poshta_branch')

        if not raw_phone or len(raw_phone.strip()) < 7:
            messages.error(request, 'Помилка: Не вказано номер телефону.')
            return redirect('store:checkout')

        digits = re.sub(r'\D', '', raw_phone)
        if not (10 <= len(digits) <= 15):
            messages.error(request, 'Помилка: Некоректний номер телефону. Введіть у форматі +380XXXXXXXXX.')
            return redirect('store:checkout')

        clean_phone = re.sub(r'[^\d\+\-\(\)\s]', '', raw_phone)

        suspicious_words = ['select', 'sleep', 'dbms_pipe', 'union', 'insert',
                            'drop', 'delete', 'update', 'chr(', '||']
        for field in [raw_name, raw_city, raw_branch]:
            if field:
                if len(field) > 100:
                    messages.error(request, 'Помилка: Занадто довгий текст у полі форми.')
                    return redirect('store:checkout')
                if any(w in field.lower() for w in suspicious_words):
                    messages.error(request, 'Система безпеки заблокувала запит.')
                    return redirect('store:checkout')

        with transaction.atomic():
            order = Order.objects.create(
                customer=request.user if request.user.is_authenticated else None,
                shipping_type=shipping_type,
                full_name=raw_name,
                phone=clean_phone,
                email=None if is_pickup else request.POST.get('email'),
                city=raw_city,
                nova_poshta_branch=raw_branch,
            )
            items_text = ""
            for item in cart:
                p = item['product']
                OrderItem.objects.create(
                    order=order, product=p,
                    quantity=item['quantity'],
                    price_at_purchase=item['price'],
                )
                items_text += (
                    f"\n🔘 {p.brand.name} {p.name} "
                    f"({p.width}/{p.profile} R{p.diameter}) — {item['quantity']} шт."
                )

        delivery_details = (
            "🏃 САМОВИВІЗ (Київ, вул. Качали 3)"
            if is_pickup
            else f"🚚 НОВА ПОШТА\n📍 Місто: {raw_city}\n🏢 Відділення: {raw_branch}"
        )
        send_telegram(
            f"🔥 <b>НОВЕ ЗАМОВЛЕННЯ #{order.id}</b>\n"
            f"👤 {order.full_name}\n📞 {order.phone}\n"
            f"➖➖➖➖➖➖\n{delivery_details}\n➖➖➖➖➖➖\n"
            f"🛒 <b>ТОВАРИ:</b>{items_text}\n➖➖➖➖➖➖\n"
            f"💰 <b>СУМА: {cart.get_total_price()} грн</b>"
        )
        cart.clear()
        return redirect('store:catalog')

    initial_data = {}
    if request.user.is_authenticated:
        initial_data['email']     = request.user.email
        initial_data['full_name'] = f"{request.user.first_name} {request.user.last_name}".strip()
        if hasattr(request.user, 'profile'):
            prof = request.user.profile
            initial_data['phone'] = getattr(prof, 'phone', getattr(prof, 'phone_number', ''))
            initial_data['city']  = getattr(prof, 'city', '')
            initial_data['nova_poshta_branch'] = getattr(prof, 'nova_poshta_branch', '')
            if not initial_data['full_name']:
                initial_data['full_name'] = getattr(prof, 'full_name', '')

    return render(request, 'store/checkout.html', {'prefill': initial_data})


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
            send_telegram(f"🆘 SOS-дзвінок: {phone}")
            return JsonResponse({'status': 'ok'})
    except json.JSONDecodeError:
        pass
    return JsonResponse({'status': 'err'}, status=400)


def sync_google_sheet_view(request):
    return redirect('admin:store_product_changelist')


def faq_view(request):
    return render(request, 'store/faq.html')


def fix_product_names_view(request):
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Тільки для адміна'}, status=403)

    batch_size = 300
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        page = 1

    start = (page - 1) * batch_size
    products = Product.objects.order_by('id')[start:start + batch_size]
    if not products:
        return JsonResponse({'status': 'done', 'message': '🎉 Всі товари перевірено!'})

    count = 0
    log   = []
    for p in products:
        raw_name   = p.name
        clean_name = raw_name.replace("Шина", "").replace("шина", "")
        if p.brand:
            clean_name = re.sub(f"^{re.escape(p.brand.name)}", "", clean_name, flags=re.IGNORECASE)
            clean_name = re.sub(rf"\({re.escape(p.brand.name)}\)", "", clean_name, flags=re.IGNORECASE)

        index_match    = re.search(r'\b(\d{2,3}[A-Z]{1,2})\b', clean_name)
        load_speed_idx = index_match.group(1) if index_match else ""

        clean_name_no_size = re.sub(r'\d{3}/\d{2}[RZ]\d{2}', '', clean_name)
        if load_speed_idx:
            clean_name_no_size = clean_name_no_size.replace(load_speed_idx, "")

        model_name = re.sub(r'^\W+|\W+$', '', clean_name_no_size.strip())
        final_name = f"{model_name} {load_speed_idx}".strip() if load_speed_idx else model_name
        final_name = re.sub(r'\s+', ' ', final_name).strip()

        if final_name != p.name and len(final_name) > 1:
            log.append(f"{p.id}: {p.name} -> {final_name}")
            Product.objects.filter(pk=p.pk).update(name=final_name)
            count += 1

    return JsonResponse({
        'status': 'processing',
        'current_page': page,
        'fixed_in_this_batch': count,
        'NEXT_STEP': f"{request.path}?page={page + 1}",
        'log': log[:20],
    })


def sitemap_xml_view(request):
    base_url = "https://r16.com.ua"
    urls = []

    static_routes = [
        ('store:home',             '1.0', 'daily'),
        ('store:catalog',          '0.9', 'daily'),
        ('store:about',            '0.5', 'monthly'),
        ('store:contacts',         '0.5', 'monthly'),
        ('store:delivery_payment', '0.5', 'monthly'),
        ('store:warranty',         '0.5', 'monthly'),
        ('store:faq',              '0.6', 'monthly'),
    ]
    for name, priority, freq in static_routes:
        try:
            urls.append({'loc': f"{base_url}{reverse(name)}", 'priority': priority, 'freq': freq})
        except Exception:
            pass

    for slug in ['zimovi', 'litni', 'vsesezonni']:
        try:
            urls.append({
                'loc': f"{base_url}{reverse('store:seo_universal', args=[slug])}",
                'priority': '0.8', 'freq': 'daily',
            })
        except Exception:
            pass

    for brand in Brand.objects.all():
        urls.append({'loc': f"{base_url}/shiny/brendy/{brand.slug}/", 'priority': '0.7', 'freq': 'weekly'})

    for product in Product.objects.exclude(slug__isnull=True).exclude(slug=''):
        urls.append({'loc': f"{base_url}/product/{product.slug}/", 'priority': '0.8', 'freq': 'weekly'})

    sizes = (Product.objects.filter(stock_quantity__gt=0)
             .values('width', 'profile', 'diameter').distinct())
    for s in sizes:
        w, p, d = s['width'], s['profile'], s['diameter']
        urls.append({'loc': f"{base_url}/shiny/{w}-{p}-r{d}/", 'priority': '0.9', 'freq': 'daily'})
        for seas in ['zimovi', 'litni', 'vsesezonni']:
            urls.append({'loc': f"{base_url}/shiny/{seas}/{w}-{p}-r{d}/", 'priority': '0.9', 'freq': 'daily'})

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u in urls:
        xml_lines.append(
            f'  <url>\n'
            f'    <loc>{u["loc"]}</loc>\n'
            f'    <changefreq>{u["freq"]}</changefreq>\n'
            f'    <priority>{u["priority"]}</priority>\n'
            f'  </url>'
        )
    xml_lines.append('</urlset>')
    return HttpResponse("\n".join(xml_lines), content_type="application/xml")


def google_shopping_feed(request):
    """
    Google Merchant Center XML фід.
    URL: https://r16.com.ua/google-feed.xml

    Підключення в Merchant Center:
      Продукти → Фіди → + → Запланована вибірка
      URL: https://r16.com.ua/google-feed.xml
      Частота: щодня
    """
    from django.utils.xmlutils import SimplerXMLGenerator
    from io import StringIO

    products = (
        Product.objects
        .filter(price__gt=0, slug__isnull=False)
        .exclude(slug='')
        .select_related('brand')
        .order_by('-id')
    )

    out = StringIO()
    handler = SimplerXMLGenerator(out, 'utf-8')
    handler.startDocument()

    handler.startElement('rss', {
        'version': '2.0',
        'xmlns:g': 'http://base.google.com/ns/1.0',
    })
    handler.startElement('channel', {})

    def el(tag, text):
        handler.startElement(tag, {})
        handler.characters(str(text))
        handler.endElement(tag)

    el('title', 'R16.com.ua — Шини з доставкою по Україні')
    el('link', 'https://r16.com.ua')
    el('description', 'Інтернет-магазин шин R16.com.ua. Зимові, літні, всесезонні шини.')

    for p in products:
        title = f"{p.brand.name} {p.display_name} {p.width}/{p.profile} R{p.diameter}"
        if len(title) > 150:
            title = title[:150]

        season_ua = {
            'winter': 'Зимова',
            'summer': 'Літня',
            'all-season': 'Всесезонна',
        }.get(p.seasonality, 'Шина')

        description = (
            f"{season_ua} шина {p.brand.name} {p.display_name}. "
            f"Розмір: {p.width}/{p.profile} R{p.diameter}. "
            f"Індекси: {p.load_index or ''}{p.speed_index or ''}. "
            f"Доставка по Україні Новою Поштою."
        )

        product_url = f"https://r16.com.ua/product/{p.slug}/"

        if getattr(p, 'photo_url', None):
            image_url = p.photo_url
        elif getattr(p, 'photo', None) and p.photo:
            image_url = f"https://r16.com.ua{p.photo.url}"
        else:
            image_url = None

        availability = 'in_stock' if p.stock_quantity > 0 else 'out_of_stock'
        price_str = f"{p.price:.2f} UAH"

        handler.startElement('item', {})

        el('g:id',          str(p.id))
        el('g:title',       title)
        el('g:description', description)
        el('g:link',        product_url)

        if image_url:
            el('g:image_link', image_url)

        el('g:availability', availability)
        el('g:price',        price_str)
        el('g:condition',    'new')
        el('g:brand',        p.brand.name)

        # Шини не мають GTIN — обов'язково, інакше Google відхилить товар
        el('g:identifier_exists', 'no')
        el('g:mpn', str(p.id))

        el('g:google_product_category',
           'Vehicles & Parts > Vehicle Parts & Accessories > Tire & Wheel Accessories > Tires')
        el('g:product_type', f"Шини > {season_ua} шини > {p.brand.name}")

        # Доставка
        handler.startElement('g:shipping', {})
        el('g:country', 'UA')
        el('g:service', 'Нова Пошта')
        el('g:price',   '0.00 UAH')
        handler.endElement('g:shipping')

        # Мітки для фільтрації в Merchant Center
        el('g:custom_label_0', p.seasonality or 'unknown')  # winter/summer/all-season
        el('g:custom_label_1', str(p.diameter))              # 15, 16, 17...
        el('g:custom_label_2', p.brand.name)                 # Michelin, Nokian...

        handler.endElement('item')

    handler.endElement('channel')
    handler.endElement('rss')

    return HttpResponse(out.getvalue(), content_type='application/xml; charset=utf-8')
