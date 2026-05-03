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
        ("Як дізнатися свій розмір шин?", "Подивись наклейку на дверях авто або на кришці бензобака..."),
        ("Що означають цифри 205/55 R16?", "205 — ширина, 55 — висота профілю, R16 — діаметр диска."),
    ],
    'winter': [("Коли переходити на зимову гуму?", "Коли температура стабільно опускається до +7°C і нижче.")],
}

# --- 🧠 SEO ШАБЛОНИ ---
SEO_TEMPLATES = {
    'winter': {'h2': 'Чому варто купити зимові шини {brand} {size}?', 'text': '<p>Опис зимових шин...</p>'},
    'summer': {'h2': 'Літні шини {brand} {size}: швидкість та контроль', 'text': '<p>Опис літніх шин...</p>'},
    'all_season': {'h2': 'Всесезонні шини {brand} {size}', 'text': '<p>Опис всесезонки...</p>'},
    'default': {'h2': 'Купити шини {brand} {size} в Києві', 'text': '<p>Магазин R16...</p>'},
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
    return {'title': f"Купити шини {brand_name} {size_str}", 'h1': f"Шини {brand_name}", 'seo_h2': "Переваги", 'description_html': "Текст", 'meta_description': "Опис", 'faq_key': 'default', 'brand_name': brand_name, 'canonical_url': "https://r16.com.ua/catalog/"}

def get_combined_faq(season_db): return FAQ_DATA['base']
def get_faq_schema_json(faq_list): return json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": []})
def get_cross_links(s, b, w, p, d): return []

# --- 👁️ VIEWS ---

def home_view(request):
    featured = Product.objects.filter(stock_quantity__gt=4).order_by('?')[:8]
    return render(request, 'store/home.html', {'featured_products': featured, 'brands': Brand.objects.all().order_by('name')})

def brand_landing_view(request, brand_slug):
    brand = get_object_or_404(Brand, Q(slug=brand_slug) | Q(name__iexact=brand_slug))
    products = Product.objects.filter(brand=brand, stock_quantity__gt=0).order_by('price')
    paginator = Paginator(products, 12)
    return render(request, 'store/brand_detail.html', {'brand': brand, 'page_obj': paginator.get_page(request.GET.get('page'))})

def seo_matrix_view(request, slug=None, brand_slug=None, season_slug=None, width=None, profile=None, diameter=None):
    products = get_base_products().order_by('status_order', '-id')
    paginator = Paginator(products, 12)
    return render(request, 'store/catalog.html', {'page_obj': paginator.get_page(request.GET.get('page'))})

def catalog_view(request): return seo_matrix_view(request)

def product_detail_view(request, slug):
    product = get_object_or_404(Product, slug=slug)
    approved_reviews = product.reviews.filter(is_approved=True)
    return render(request, 'store/product_detail.html', {'product': product, 'reviews': approved_reviews})

def cart_detail_view(request): return render(request, 'store/cart.html', {'cart': Cart(request)})

@require_POST
def cart_add_view(request, product_id):
    cart = Cart(request)
    cart.add(get_object_or_404(Product, id=product_id), int(request.POST.get('quantity', 1)))
    return redirect('store:cart_detail')

def checkout_view(request):
    cart = Cart(request)
    if request.method == 'POST':
        cart.clear()
        return redirect('store:home')
    return render(request, 'store/checkout.html', {'cart': cart})

# 🔥 ТЕХНІЧНІ СТОРІНКИ 🔥
def about_view(request): return render(request, 'store/about.html')
def contacts_view(request): return render(request, 'store/contacts.html')
def delivery_payment_view(request): return render(request, 'store/delivery_payment.html')
def warranty_view(request): return render(request, 'store/warranty.html')
def faq_view(request): return render(request, 'store/faq.html')

@require_POST
def bot_callback_view(request): return JsonResponse({'status': 'ok'})

# 🔥 SUPER-SAFE SITEMAP.XML (Більше ніяких 500) 🔥
def sitemap_xml_view(request):
    base_url = "https://r16.com.ua"
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]

    # 1. Статичні (ручне додавання)
    for path in ['', '/catalog/', '/about/', '/contacts/', '/delivery/', '/warranty/', '/faq/']:
        xml_lines.append(f'  <url><loc>{base_url}{path}</loc><changefreq>daily</changefreq><priority>0.9</priority></url>')

    # 2. Сезони
    for slug in ['zimovi', 'litni', 'vsesezonni']:
        xml_lines.append(f'  <url><loc>{base_url}/shiny/{slug}/</loc><changefreq>daily</changefreq><priority>0.8</priority></url>')

    # 3. Бренди (Safe Loop)
    for b in Brand.objects.exclude(slug='').values('slug'):
        xml_lines.append(f'  <url><loc>{base_url}/shiny/brendy/{b["slug"]}/</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>')

    # 4. Товари (Safe Loop)
    for p in Product.objects.exclude(slug='').values('slug'):
        xml_lines.append(f'  <url><loc>{base_url}/product/{p["slug"]}/</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>')

    # 5. Розміри (Тільки в наявності)
    sizes = Product.objects.filter(stock_quantity__gt=0).values('width', 'profile', 'diameter').distinct()
    for s in sizes:
        xml_lines.append(f'  <url><loc>{base_url}/shiny/{s["width"]}-{s["profile"]}-r{s["diameter"]}/</loc><changefreq>daily</changefreq><priority>0.9</priority></url>')

    xml_lines.append('</urlset>')
    
    # Використовуємо .replace для безпеки, якщо в слагах є амперсанди
    content = "\n".join(xml_lines).replace('&', '&amp;')
    return HttpResponse(content, content_type="application/xml")


# 🔥 ОНОВЛЕНИЙ ГУГЛ ФІД 🔥
def google_shopping_feed(request):
    products = Product.objects.filter(price__gt=0, stock_quantity__gt=0, slug__isnull=False).select_related('brand').order_by('-stock_quantity')
    out = StringIO()
    handler = SimplerXMLGenerator(out, 'utf-8')
    handler.startDocument()
    handler.startElement('rss', {'version': '2.0', 'xmlns:g': 'http://base.google.com/ns/1.0'})
    handler.startElement('channel', {})

    handler.startElement('title', {})
    handler.characters('R16.com.ua')
    handler.endElement('title')

    for p in products:
        try:
            description = re.sub('<[^<]+?>', '', p.description or "")[:5000]
            image_url = f"https://r16.com.ua{p.photo.url}" if p.photo else (p.photo_url if p.photo_url else None)
            if not image_url: continue

            handler.startElement('item', {})
            handler.startElement('g:id', {})
            handler.characters(str(p.id))
            handler.endElement('g:id')

            handler.startElement('g:title', {})
            handler.characters(f"{p.brand.name} {p.name} {p.width}/{p.profile} R{p.diameter}")
            handler.endElement('g:title')

            handler.startElement('g:description', {})
            handler.characters(description)
            handler.endElement('g:description')

            handler.startElement('g:link', {})
            handler.characters(f"https://r16.com.ua/product/{p.slug}/")
            handler.endElement('g:link')

            handler.startElement('g:image_link', {})
            handler.characters(image_url)
            handler.endElement('g:image_link')

            handler.startElement('g:availability', {})
            handler.characters('in stock')
            handler.endElement('g:availability')

            handler.startElement('g:price', {})
            handler.characters(f"{p.price:.2f} UAH")
            handler.endElement('g:price')

            handler.startElement('g:brand', {})
            handler.characters(p.brand.name)
            handler.endElement('g:brand')

            handler.startElement('g:google_product_category', {})
            handler.characters('6093')
            handler.endElement('g:google_product_category')

            handler.startElement('g:condition', {})
            handler.characters('new')
            handler.endElement('g:condition')
            handler.endElement('item')
        except Exception:
            continue

    handler.endElement('channel')
    handler.endElement('rss')
    return HttpResponse(out.getvalue(), content_type='application/xml; charset=utf-8')

def robots_txt(request):
    return HttpResponse("User-agent: *\nDisallow: /admin/\nSitemap: https://r16.com.ua/sitemap.xml", content_type="text/plain")

def redirect_old_product_urls(request, product_id):
    p = get_object_or_404(Product, id=product_id)
    return redirect('store:product_detail', slug=p.slug, permanent=True)

def fix_product_names_view(request): return JsonResponse({'status': 'ok'})
def sync_google_sheet_view(request): return redirect('admin:store_product_changelist')
