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
from django.utils.xmlutils import SimplerXMLGenerator
from io import StringIO
import json
import requests
import re
import logging

logger = logging.getLogger(__name__)

from .cart import Cart
from .models import Product, Order, OrderItem, Brand, SiteBanner, AboutImage, Review

# --- ⚙️ КОНФІГУРАЦІЯ ---
SEASONS_MAP = {
    'zimovi':      {'db': 'winter',     'ua': 'Зимові шини',     'adj': 'зимові'},
    'zymovi':      {'db': 'winter',     'ua': 'Зимові шини',     'adj': 'зимові'},
    'litni':       {'db': 'summer',     'ua': 'Літні шини',      'adj': 'літні'},
    'vsesezonni': {'db': 'all-season', 'ua': 'Всесезонні шини', 'adj': 'всесезонні'},
}

DB_TO_SLUG_MAP = {
    'winter':      'zimovi',
    'summer':      'litni',
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
        ("Яки літні шини кращі: для міста чи траси?",
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
        if not token or not chat_id: return
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      data={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}, timeout=5)
    except Exception: pass

def get_base_products():
    return Product.objects.filter(width__gt=0, diameter__gt=0).annotate(
        status_order=Case(When(stock_quantity__gt=0, then=Value(0)), default=Value(1), output_field=IntegerField())
    )

def generate_seo_content(brand_obj=None, season_db=None, w=None, p=None, d=None, min_price=0, max_price=0):
    brand_name = brand_obj.name if brand_obj else "R16"
    size_str = f"{w}/{p} R{d}" if (w and p and d) else ""
    h1 = f"Купити шини {brand_name} {size_str}".strip()
    key = 'default'
    if season_db == 'winter': key = 'winter'
    elif season_db == 'summer': key = 'summer'
    elif season_db in ('all-season', 'all_season'): key = 'all_season'
    template = SEO_TEMPLATES[key]
    fmt = {'brand': brand_name, 'size': size_str}
    return {
        'title': f"{h1} | R16.com.ua", 'h1': h1, 'seo_h2': template['h2'].format(**fmt),
        'description_html': template['text'].format(**fmt), 'meta_description': f"{h1} в наявності.",
        'canonical_url': "https://r16.com.ua/catalog/", 'brand_name': brand_name, 'faq_key': key
    }

def get_combined_faq(season_db):
    faq_list = FAQ_DATA['base'].copy()
    if season_db in FAQ_DATA: faq_list.extend(FAQ_DATA[season_db])
    return faq_list

def get_faq_schema_json(faq_list):
    schema_items = []
    for q, a in faq_list:
        schema_items.append({"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub('<[^<]+?>', '', a)}})
    return json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": schema_items}, ensure_ascii=False)

def get_cross_links(s, b, w, p, d): return []

# --- 👁️ VIEWS ---
def home_view(request):
    featured = Product.objects.filter(stock_quantity__gt=4).order_by('?')[:8]
    return render(request, 'store/home.html', {
        'featured_products': featured, 'brands': Brand.objects.all().order_by('name'),
        'all_widths': Product.objects.filter(width__gt=0).values_list('width', flat=True).distinct().order_by('width'),
        'all_profiles': Product.objects.filter(profile__gt=0).values_list('profile', flat=True).distinct().order_by('profile'),
        'all_diameters': Product.objects.filter(diameter__gt=0).values_list('diameter', flat=True).distinct().order_by('diameter'),
    })

def catalog_view(request):
    return seo_matrix_view(request)

def brand_landing_view(request, brand_slug):
    brand = get_object_or_404(Brand, Q(slug=brand_slug) | Q(name__iexact=brand_slug))
    products = Product.objects.filter(brand=brand, stock_quantity__gt=0).order_by('price')
    paginator = Paginator(products, 12)
    return render(request, 'store/brand_detail.html', {'brand': brand, 'page_obj': paginator.get_page(request.GET.get('page'))})

def seo_matrix_view(request, slug=None, brand_slug=None, season_slug=None, width=None, profile=None, diameter=None):
    products = get_base_products().order_by('status_order', '-id')
    paginator = Paginator(products, 12)
    return render(request, 'store/catalog.html', {'page_obj': paginator.get_page(request.GET.get('page'))})

def product_detail_view(request, slug):
    product = get_object_or_404(Product, slug=slug)
    if request.method == 'POST' and 'submit_review' in request.POST:
        Review.objects.create(product=product, name=request.POST.get('reviewer_name'), rating=int(request.POST.get('rating', 5)), text=request.POST.get('review_text'))
        messages.success(request, 'Відгук на модерації.')
        return redirect('store:product_detail', slug=product.slug)
    approved_reviews = product.reviews.filter(is_approved=True)
    return render(request, 'store/product_detail.html', {'product': product, 'reviews': approved_reviews})

# --- 🛒 CART & CHECKOUT ---
def cart_detail_view(request): return render(request, 'store/cart.html', {'cart': Cart(request)})

@require_POST
def cart_add_view(request, product_id):
    Cart(request).add(get_object_or_404(Product, id=product_id), int(request.POST.get('quantity', 1)))
    return redirect('store:cart_detail')

def cart_remove_view(request, product_id):
    Cart(request).remove(get_object_or_404(Product, id=product_id))
    return redirect('store:cart_detail')

def cart_add_ajax_view(request, product_id):
    Cart(request).add(get_object_or_404(Product, id=product_id), int(request.POST.get('quantity', 1)))
    return JsonResponse({'cart_len': len(Cart(request))})

def checkout_view(request):
    cart = Cart(request)
    if request.method == 'POST':
        order = Order.objects.create(full_name=request.POST.get('full_name'), phone=request.POST.get('phone'), city=request.POST.get('city'))
        send_telegram(f"Нове замовлення #{order.id}")
        cart.clear()
        return redirect('store:home')
    return render(request, 'store/checkout.html', {'cart': cart})

# --- 📄 STATIC PAGES ---
def about_view(request): return render(request, 'store/about.html', {'photos': AboutImage.objects.all()})
def contacts_view(request): return render(request, 'store/contacts.html')
def delivery_payment_view(request): return render(request, 'store/delivery_payment.html')
def warranty_view(request): return render(request, 'store/warranty.html')
def faq_view(request): return render(request, 'store/faq.html')

# --- 🛠️ ТЕХНІЧНІ (SITEMAP & FEED) ---
def sitemap_xml_view(request):
    base_url = "https://r16.com.ua"
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path in ['', '/catalog/', '/about/', '/contacts/']:
        xml.append(f'  <url><loc>{base_url}{path}</loc><changefreq>daily</changefreq></url>')
    # Додаємо тільки перші 2000 товарів для стабільності
    for p_slug in Product.objects.exclude(slug='').values_list('slug', flat=True)[:2000]:
        xml.append(f'  <url><loc>{base_url}/product/{p_slug}/</loc></url>')
    xml.append('</urlset>')
    return HttpResponse("\n".join(xml), content_type="application/xml")

def google_shopping_feed(request):
    products = Product.objects.filter(price__gt=0, stock_quantity__gt=0, slug__isnull=False).select_related('brand')[:2000]
    out = StringIO()
    handler = SimplerXMLGenerator(out, 'utf-8')
    handler.startDocument()
    handler.startElement('rss', {'version': '2.0', 'xmlns:g': 'http://base.google.com/ns/1.0'})
    handler.startElement('channel', {})
    handler.startElement('title', {}); handler.characters('R16.com.ua'); handler.endElement('title')
    for p in products:
        try:
            handler.startElement('item', {})
            handler.startElement('g:id', {}); handler.characters(str(p.id)); handler.endElement('g:id')
            handler.startElement('g:title', {}); handler.characters(f"{p.brand.name} {p.name}"); handler.endElement('g:title')
            handler.startElement('g:link', {}); handler.characters(f"{base_url}/product/{p.slug}/"); handler.endElement('g:link')
            handler.startElement('g:price', {}); handler.characters(f"{p.price:.2f} UAH"); handler.endElement('g:price')
            handler.startElement('g:availability', {}); handler.characters('in stock'); handler.endElement('g:availability')
            handler.endElement('item')
        except: continue
    handler.endElement('channel'); handler.endElement('rss')
    return HttpResponse(out.getvalue(), content_type='application/xml')

def robots_txt(request):
    return HttpResponse("User-agent: *\nDisallow: /admin/\nSitemap: https://r16.com.ua/sitemap.xml", content_type="text/plain")

def redirect_old_product_urls(request, product_id):
    p = get_object_or_404(Product, id=product_id)
    return redirect('store:product_detail', slug=p.slug, permanent=True)

def fix_product_names_view(request): return JsonResponse({'ok': True})
def bot_callback_view(request): return JsonResponse({'ok': True})
def sync_google_sheet_view(request): return redirect('admin:store_product_changelist')
def cart_update_quantity_view(request, product_id): return redirect('store:cart_detail')
