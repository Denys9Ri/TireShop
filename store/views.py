from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
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
    'zimovi': {'db': 'winter', 'ua': 'Зимові шини', 'adj': 'зимові'},
    'winter': {'db': 'winter', 'ua': 'Зимові шини', 'adj': 'зимові'},
    
    'litni': {'db': 'summer', 'ua': 'Літні шини', 'adj': 'літні'},
    'summer': {'db': 'summer', 'ua': 'Літні шини', 'adj': 'літні'},
    
    'vsesezonni': {'db': 'all_season', 'ua': 'Всесезонні шини', 'adj': 'всесезонні'},
    'all-season': {'db': 'all_season', 'ua': 'Всесезонні шини', 'adj': 'всесезонні'},
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
        ("Що означає “під шип”?", "Це модель, яку можна шипувати. Користь — якщо реально є лід чи частий сильний мороз."),
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

# --- 🛠️ ДОПОМІЖНІ ФУНКЦІЇ ---
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

def generate_seo_content(brand_obj=None, season_db=None, w=None, p=None, d=None, min_price=0, max_price=0):
    brand_name = brand_obj.name if brand_obj else "Всі бренди"
    size_str = f"{w}/{p} R{d}" if (w and p and d) else ""
    
    key = season_db if season_db in SEO_TEMPLATES else 'default'
    template = SEO_TEMPLATES[key]

    # --- ФОРМУВАННЯ БАЗОВОГО ЗАГОЛОВКА ---
    h1_parts = []
    if season_db == 'winter': h1_parts.append("Зимові шини")
    elif season_db == 'summer': h1_parts.append("Літні шини")
    elif season_db == 'all_season': h1_parts.append("Всесезонні шини")
    else: h1_parts.append("Шини")
    
    if brand_obj: h1_parts.append(brand_obj.name)
    if size_str: h1_parts.append(size_str)
    
    h1_final = " ".join(h1_parts)
    title_final = f"{h1_final} — Ціна від {min_price} грн | R16.com.ua"
    description_html = ""
    seo_h2 = ""

    # 🔥 ПОКРАЩЕНА SEO ЛОГІКА (ГЕНЕРАЦІЯ КОНТЕНТУ) 🔥
    if size_str and not brand_obj and not season_db:
        title_final = f"Купити резину {size_str} Київ — Ціна від {min_price} грн"
        seo_h2 = f"Гума {size_str}: ТОП пропозиції"
        description_html = f"<p>Шукаєте надійні <b>шини {size_str}</b>? У нас великий вибір гуми цього розміру. 🚗 В наявності зимові, літні та всесезонні моделі.</p>"
    elif size_str and season_db and not brand_obj:
        if season_db == 'winter':
            title_final = f"Купити зимові шини {size_str} Київ — Ціна від {min_price} грн"
            seo_h2 = f"Зимова гума {size_str}: Безпека на снігу"
            description_html = f"<p>Шукаєте <b>зимові шини {size_str}</b>? Великий вибір: шиповані та фрикційні. ❄️ Гарантія та шиномонтаж.</p>"
        elif season_db == 'summer':
            title_final = f"Купити літні шини {size_str} Київ — Ціна від {min_price} грн"
            seo_h2 = f"Літня гума {size_str}: Комфорт та швидкість"
            description_html = f"<p>Обирайте <b>літні шини {size_str}</b>. Захист від аквапланування, економія пального. ☀️ Кращі бренди.</p>"
        elif season_db == 'all_season':
            title_final = f"Купити всесезонні шини {size_str} Київ — Ціна від {min_price} грн"
            seo_h2 = f"Всесезонка {size_str}: Один комплект на рік"
            description_html = f"<p>Універсальні <b>всесезонні шини {size_str}</b>. Економія на перевзуванні. 🌤 Ідеально для м'якої зими.</p>"
    elif size_str and brand_obj and not season_db:
        title_final = f"Шини {brand_name} {size_str} — Купити в Києві, Ціна"
        seo_h2 = f"Гума {brand_name} {size_str}: Огляд моделей"
        description_html = f"<p>Каталог шин <b>{brand_name}</b> у розмірі <b>{size_str}</b>. Оригінальна якість, гарантія від виробника. 🚚 Швидка доставка.</p>"
    elif size_str and brand_obj and season_db:
        if season_db == 'winter':
             title_final = f"Зимові шини {brand_name} {size_str} — Ціна від {min_price} грн"
             seo_h2 = f"Купити зимову гуму {brand_name} {size_str}"
             description_html = f"<p>Оригінальні <b>зимові шини {brand_name} {size_str}</b>. Максимальне зчеплення на льоду та снігу. 🏁 Офіційна гарантія.</p>"
        elif season_db == 'summer':
             title_final = f"Літні шини {brand_name} {size_str} — Ціна від {min_price} грн"
             seo_h2 = f"Літня гума {brand_name} {size_str} в наявності"
             description_html = f"<p>Обирайте <b>літні шини {brand_name} {size_str}</b> для безпечних поїздок. Стійкість до аквапланування та комфорт.</p>"
        else:
             title_final = f"Всесезонні шини {brand_name} {size_str} — Краща ціна"
             seo_h2 = f"Всесезонка {brand_name} {size_str}"
             description_html = f"<p>Практичний вибір: <b>всесезонні шини {brand_name} {size_str}</b>. Забудьте про черги на шиномонтаж.</p>"
    else:
        try:
            description_html = template['text'].format(brand=brand_name, size=size_str)
            seo_h2 = template['h2'].format(brand=brand_name, size=size_str)
        except:
            description_html = SEO_TEMPLATES['default']['text'].format(brand=brand_name, size=size_str)
            seo_h2 = h1_final

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
    elif season_db == 'all_season' or season_db == 'all-season': faq_list.extend(FAQ_DATA['all_season'])
    return faq_list

def get_faq_schema_json(faq_list):
    schema_items = []
    for q, a in faq_list:
        clean_a = re.sub('<[^<]+?>', '', a)
        schema_items.append({"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": clean_a}})
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": schema_items}
    return json.dumps(faq)

# 🔥 РОЗУМНА ПЕРЕЛІНКОВКА (НОВА ФУНКЦІЯ) 🔥
def get_cross_links(current_season_slug, current_brand, w, p, d):
    links = []
    
    # 1. Якщо ми на сторінці БРЕНДУ (але не розміру): показуємо популярні розміри ЦЬОГО бренду
    if current_brand and not w:
        # Шукаємо розміри, які реально є у цього бренду
        sizes = Product.objects.filter(brand=current_brand, stock_quantity__gt=0)\
            .values('width', 'profile', 'diameter')\
            .annotate(count=Count('id'))\
            .order_by('-count')[:15] # Топ 15 розмірів
            
        if sizes:
            group = {'title': f'Популярні розміри {current_brand.name}:', 'items': []}
            for s in sizes:
                sw, sp, sd = s['width'], s['profile'], s['diameter']
                text = f"{sw}/{sp} R{sd}"
                # Генеруємо URL: /shiny/brand/size/
                url = reverse('store:seo_brand_size', args=[current_brand.slug, sw, sp, sd])
                group['items'].append({'text': text, 'url': url})
            links.append(group)
            
        # Додаємо лінки на СЕЗОНИ цього бренду
        group_seasons = {'title': f'Сезони {current_brand.name}:', 'items': []}
        group_seasons['items'].append({'text': f'Зимові {current_brand.name}', 'url': reverse('store:seo_brand_season', args=[current_brand.slug, 'zimovi'])})
        group_seasons['items'].append({'text': f'Літні {current_brand.name}', 'url': reverse('store:seo_brand_season', args=[current_brand.slug, 'litni'])})
        links.append(group_seasons)

    # 2. Якщо ми на сторінці РОЗМІРУ (але не бренду): показуємо БРЕНДИ в цьому розмірі
    elif w and p and d and not current_brand:
        # Шукаємо бренди, у яких є цей розмір
        brands = Brand.objects.filter(product__width=w, product__profile=p, product__diameter=d, product__stock_quantity__gt=0)\
            .distinct().order_by('name')
            
        if brands:
            group = {'title': f'Бренди у розмірі {w}/{p} R{d}:', 'items': []}
            for b in brands:
                text = b.name
                # Генеруємо URL: /shiny/brand/size/
                url = reverse('store:seo_brand_size', args=[b.slug, w, p, d])
                group['items'].append({'text': text, 'url': url})
            links.append(group)
            
        # Додаємо лінки на СЕЗОНИ в цьому розмірі
        group_seasons = {'title': f'Сезонність {w}/{p} R{d}:', 'items': []}
        group_seasons['items'].append({'text': f'Зимові {w}/{p} R{d}', 'url': reverse('store:seo_season_size', args=['zimovi', w, p, d])})
        group_seasons['items'].append({'text': f'Літні {w}/{p} R{d}', 'url': reverse('store:seo_season_size', args=['litni', w, p, d])})
        links.append(group_seasons)

    # 3. Якщо просто каталог (або нічого не підійшло): показуємо загальні популярні розміри
    if not links:
        top_sizes = [
            (175, 70, 13), (185, 65, 14), (185, 65, 15), 
            (195, 65, 15), (205, 55, 16), (215, 60, 16), 
            (225, 45, 17), (225, 50, 17), (235, 55, 18)
        ]
        group = {'title': 'Популярні розміри:', 'items': []}
        for sw, sp, sd in top_sizes:
            text = f"R{sd} {sw}/{sp}"
            url = reverse('store:seo_size', args=[sw, sp, sd])
            group['items'].append({'text': text, 'url': url})
        links.append(group)
        
    return links

# 🔥 НОВА ФУНКЦІЯ: БРЕНДОВА СТОРІНКА 🔥
def brand_landing_view(request, brand_slug):
    brand = Brand.objects.filter(Q(slug=brand_slug) | Q(name__iexact=brand_slug)).first()
    if not brand: raise Http404("Бренд не знайдено")
    
    products = Product.objects.filter(brand=brand, stock_quantity__gt=0).order_by('price')
    
    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    custom_page_range = page_obj.paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1)

    seo_title = brand.seo_title if brand.seo_title else f"Шини {brand.name} ({brand.country or 'Світ'}) — Купити в Києві | Відгуки, Ціни"
    seo_h1 = brand.seo_h1 if brand.seo_h1 else f"Шини {brand.name}"
    
    if brand.description:
         short_desc = brand.description[:150] + "..."
         meta_desc = f"{short_desc} 💰 Каталог шин {brand.name} в наявності."
    else:
         meta_desc = f"Все про бренд {brand.name}: країна {brand.country}, для кого підходить, плюси та мінуси. 💰 Каталог шин {brand.name} в наявності."
    
    # Додаємо перелінковку для сторінки бренду
    cross_links = get_cross_links(None, brand, None, None, None)

    return render(request, 'store/brand_detail.html', {
        'brand': brand,
        'page_obj': page_obj,
        'custom_page_range': custom_page_range,
        'seo_title': seo_title,
        'seo_h1': seo_h1,
        'meta_description': meta_desc,
        'cross_links': cross_links, # Передаємо лінки в шаблон
    })

# --- 🔥 ГОЛОВНИЙ КОНТРОЛЕР (SEO + ПОШУК + ФІЛЬТРИ) 🔥 ---
def seo_matrix_view(request, slug=None, brand_slug=None, season_slug=None, width=None, profile=None, diameter=None):
    products = get_base_products()
    brand_obj = None
    season_db = None

    # 1. ОБРОБКА SEO URL
    if slug:
        if slug in SEASONS_MAP: season_slug = slug
        else:
            brand_obj = Brand.objects.filter(name__iexact=slug).first()
            if brand_obj: brand_slug = slug

    # 2. ПОШУК
    query = request.GET.get('query', '').strip()
    if query:
        clean = re.sub(r'[/\sR\-]', '', query, flags=re.IGNORECASE)
        match = re.fullmatch(r'(\d{6,7})', clean)
        if match:
            d = match.group(1)
            products = products.filter(width=int(d[:3]), profile=int(d[3:5]), diameter=int(d[5:]))
        else:
            products = products.filter(Q(name__icontains=query) | Q(brand__name__icontains=query))

    # 3. ФІЛЬТРИ
    if not brand_obj:
        s_brand_id = request.GET.get('brand')
        if s_brand_id: 
            products = products.filter(brand__id=s_brand_id)
            brand_obj = Brand.objects.filter(id=s_brand_id).first()
    else:
        products = products.filter(brand=brand_obj)

    if not season_slug:
        s_season = request.GET.get('season')
        if s_season:
            products = products.filter(seasonality=s_season)
            for k, v in SEASONS_MAP.items():
                if v['db'] == s_season:
                    season_slug = k
                    season_db = s_season
                    break
    elif season_slug in SEASONS_MAP:
        season_db = SEASONS_MAP[season_slug]['db']
        products = products.filter(seasonality=season_db)

    req_width = width or request.GET.get('width')
    req_profile = profile or request.GET.get('profile')
    req_diameter = diameter or request.GET.get('diameter')

    if req_width: products = products.filter(width=req_width)
    if req_profile: products = products.filter(profile=req_profile)
    if req_diameter: products = products.filter(diameter=req_diameter)

    # --- СТАТИСТИКА ---
    real_products = products.filter(price__gt=0)
    if real_products.exists():
        stats = real_products.aggregate(min_price=Min('price'), max_price=Max('price'))
        min_price = stats['min_price']
        max_price = stats['max_price']
    else:
        min_price = 0; max_price = 0

    # --- SEO DATA ---
    w_int = int(req_width) if req_width else None
    p_int = int(req_profile) if req_profile else None
    d_int = int(req_diameter) if req_diameter else None

    seo_data = generate_seo_content(brand_obj, season_db, w_int, p_int, d_int, int(min_price), int(max_price))
    
    # FAQ
    faq_list = get_combined_faq(season_db)
    faq_schema = get_faq_schema_json(faq_list)
    
    cross_links = get_cross_links(season_slug, brand_obj, w_int, p_int, d_int)

    # --- СОРТУВАННЯ ---
    ordering = request.GET.get('ordering')
    if ordering == 'cheap':
        products = products.filter(stock_quantity__gt=0).order_by('price')
    elif ordering == 'expensive':
        products = products.filter(stock_quantity__gt=0).order_by('-price')
    else:
        products = products.order_by('status_order', '-id')

    # --- UI ---
    brands = Brand.objects.all().order_by('name')
    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    # 🔥 ГЕНЕРУЄМО РОЗУМНУ ПАГІНАЦІЮ [1, '...', 5, 6, 7, '...', 20] 🔥
    custom_page_range = page_obj.paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1)
    
    q_params = request.GET.copy()
    if 'page' in q_params: del q_params['page']

    return render(request, 'store/catalog.html', {
        'page_obj': page_obj, 
        'custom_page_range': custom_page_range, 
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
        'faq_list': faq_list, 
        'cross_links': cross_links,
        'is_seo_page': True
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
        'seo_text_html': seo_data['description_html'], 
        'faq_schema': faq_schema 
    })

def redirect_old_product_urls(request, product_id):
    p = get_object_or_404(Product, id=product_id)
    return redirect('store:product_detail', slug=p.slug, permanent=True)

# --- 🛒 CART LOGIC ---
def cart_detail_view(request): return render(request, 'store/cart.html', {'cart': Cart(request)})

@require_POST
def cart_add_view(request, product_id):
    cart = Cart(request); cart.add(get_object_or_404(Product, id=product_id), int(request.POST.get('quantity', 1)))
    return redirect(request.META.get('HTTP_REFERER', 'store:catalog'))

@require_POST
def cart_update_quantity_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    try:
        quantity = int(request.POST.get('quantity', 1))
        # Ліміт на складі
        if quantity > product.stock_quantity: quantity = product.stock_quantity
        if quantity < 1: quantity = 1
        cart.add(product, quantity, update_quantity=True)
    except ValueError: pass
    return redirect('store:cart_detail')

def cart_remove_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('store:cart_detail')

# 🔥 AJAX CART VIEW 🔥
def cart_add_ajax_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    try: quantity_to_add = int(request.POST.get('quantity', 1))
    except: quantity_to_add = 1
    
    cart_item = cart.cart.get(str(product.id))
    current_in_cart = cart_item['quantity'] if cart_item else 0
    total_wanted = current_in_cart + quantity_to_add
    
    if total_wanted > product.stock_quantity:
        quantity_to_add = product.stock_quantity - current_in_cart
        if quantity_to_add < 0: quantity_to_add = 0

    if quantity_to_add > 0:
        cart.add(product=product, quantity=quantity_to_add, update_quantity=False)
    
    html = render_to_string('store/includes/cart_offcanvas.html', {'cart': cart}, request=request)
    return JsonResponse({'html': html, 'cart_len': len(cart)})

# --- ЗАМОВЛЕННЯ (CHECKOUT) ---
def checkout_view(request):
    cart = Cart(request)
    if not cart: return redirect('store:catalog')
    
    if request.method == 'POST':
        shipping_type = request.POST.get('shipping_type', 'pickup') 
        is_pickup = (shipping_type == 'pickup')
        
        order = Order.objects.create(
            customer=request.user if request.user.is_authenticated else None,
            shipping_type=shipping_type,
            full_name=request.POST.get('pickup_name') if is_pickup else request.POST.get('full_name'),
            phone=request.POST.get('pickup_phone') if is_pickup else request.POST.get('phone'),
            email=None if is_pickup else request.POST.get('email'),
            city="Київ (Самовивіз)" if is_pickup else request.POST.get('city'),
            nova_poshta_branch="-" if is_pickup else request.POST.get('nova_poshta_branch')
        )

        items_text = ""
        for item in cart:
            p = item['product']
            OrderItem.objects.create(order=order, product=p, quantity=item['quantity'], price_at_purchase=item['price'])
            items_text += f"\n🔘 {p.brand.name} {p.name} ({p.width}/{p.profile} R{p.diameter}) — {item['quantity']} шт."

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
        return redirect('store:catalog')

    initial_data = {}
    if request.user.is_authenticated:
        initial_data['email'] = request.user.email
        initial_data['full_name'] = f"{request.user.first_name} {request.user.last_name}".strip()
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            initial_data['phone'] = getattr(profile, 'phone', getattr(profile, 'phone_number', ''))
            initial_data['city'] = getattr(profile, 'city', '')
            initial_data['nova_poshta_branch'] = getattr(profile, 'nova_poshta_branch', '')
            if not initial_data['full_name']: initial_data['full_name'] = getattr(profile, 'full_name', '')

    return render(request, 'store/checkout.html', {'user_data': initial_data})

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
def faq_view(request): return render(request, 'store/faq.html')

def fix_product_names_view(request):
    if not request.user.is_superuser: return JsonResponse({'status': 'error', 'message': 'Тільки для адміна'})
    from .models import Product
    import re
    batch_size = 300
    try: page = int(request.GET.get('page', 1))
    except ValueError: page = 1
    start_index = (page - 1) * batch_size
    end_index = start_index + batch_size
    products = Product.objects.order_by('id')[start_index:end_index]
    if not products: return JsonResponse({'status': 'done', 'message': '🎉 Всі товари перевірено!'})
    count = 0; log = []
    for p in products:
        raw_name = p.name
        clean_name = raw_name.replace("Шина", "").replace("шина", "")
        if p.brand:
            clean_name = re.sub(f"^{p.brand.name}", "", clean_name, flags=re.IGNORECASE)
            clean_name = re.sub(f"\({p.brand.name}\)", "", clean_name, flags=re.IGNORECASE)
        index_match = re.search(r'\b(\d{2,3}[A-Z]{1,2})\b', clean_name)
        load_speed_idx = ""
        if index_match: load_speed_idx = index_match.group(1)
        clean_name_no_size = re.sub(r'\d{3}/\d{2}[R|Z]\d{2}', '', clean_name)
        if load_speed_idx: clean_name_no_size = clean_name_no_size.replace(load_speed_idx, "")
        model_name = clean_name_no_size.strip()
        model_name = re.sub(r'^\W+|\W+$', '', model_name)
        final_name = model_name
        if load_speed_idx: final_name += f" {load_speed_idx}"
        final_name = re.sub(r'\s+', ' ', final_name).strip()
        if final_name != p.name and len(final_name) > 1:
            log.append(f"{p.id}: {p.name} -> {final_name}")
            p.name = final_name
            p.save()
            count += 1
    next_page = page + 1
    next_link = f"{request.path}?page={next_page}"
    return JsonResponse({'status': 'processing', 'current_page': page, 'fixed_in_this_batch': count, 'NEXT_STEP': f"Перейдіть сюди: {next_link}", 'log': log[:20]})
