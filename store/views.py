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

# --- 📚 FAQ (Твої дані) ---
FAQ_DATA = {
    'base': [
        ("Як дізнатися свій розмір шин?", "Подивись наклейку на дверях авто або на кришці бензобака..."),
        ("Що означають цифри 205/55 R16?", "205 — ширина, 55 — висота профілю, R16 — діаметр диска.")
    ]
}

# --- 🛠️ ДОПОМІЖНІ ФУНКЦІЇ ---
def get_base_products():
    return Product.objects.filter(width__gt=0, diameter__gt=0).annotate(
        status_order=Case(When(stock_quantity__gt=0, then=Value(0)), default=Value(1), output_field=IntegerField())
    )

def send_telegram(message):
    try:
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', None)
        if token and chat_id:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          data={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}, timeout=5)
    except Exception: pass

# --- 👁️ VIEWS ---
def home_view(request):
    featured = Product.objects.filter(stock_quantity__gt=4).order_by('?')[:8]
    return render(request, 'store/home.html', {'featured_products': featured, 'brands': Brand.objects.all().order_by('name')})

def catalog_view(request):
    products = get_base_products().order_by('status_order', '-id')
    paginator = Paginator(products, 12)
    return render(request, 'store/catalog.html', {'page_obj': paginator.get_page(request.GET.get('page'))})

def brand_landing_view(request, brand_slug):
    brand = get_object_or_404(Brand, Q(slug=brand_slug) | Q(name__iexact=brand_slug))
    products = Product.objects.filter(brand=brand, stock_quantity__gt=0).order_by('price')
    paginator = Paginator(products, 12)
    return render(request, 'store/brand_detail.html', {'brand': brand, 'page_obj': paginator.get_page(request.GET.get('page'))})

def seo_matrix_view(request, slug=None, brand_slug=None, season_slug=None, width=None, profile=None, diameter=None):
    return catalog_view(request)

def product_detail_view(request, slug):
    product = get_object_or_404(Product, slug=slug)
    approved_reviews = product.reviews.filter(is_approved=True)
    return render(request, 'store/product_detail.html', {'product': product, 'reviews': approved_reviews})

# --- 🛒 КОРЗИНА ---
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

# 🔥 SITEMAP (БЕЗПЕЧНА ВЕРСІЯ) 🔥
def sitemap_xml_view(request):
    base_url = "https://r16.com.ua"
    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    
    # Головні сторінки
    static = ['', '/catalog/', '/about/', '/contacts/']
    for p in static:
        xml_lines.append(f'  <url><loc>{base_url}{p}</loc><changefreq>daily</changefreq></url>')

    # Товари (беремо тільки перші 1000 для тесту пам'яті)
    products = Product.objects.exclude(slug='').values_list('slug', flat=True)[:1000]
    for ps in products:
        xml_lines.append(f'  <url><loc>{base_url}/product/{ps}/</loc></url>')

    xml_lines.append('</urlset>')
    return HttpResponse("\n".join(xml_lines), content_type="application/xml")

# 🔥 ГУГЛ ФІД 🔥
def google_shopping_feed(request):
    products = Product.objects.filter(price__gt=0, stock_quantity__gt=0, slug__isnull=False).select_related('brand')
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
            handler.startElement('g:link', {}); handler.characters(f"https://r16.com.ua/product/{p.slug}/"); handler.endElement('g:link')
            handler.startElement('g:price', {}); handler.characters(f"{p.price:.2f} UAH"); handler.endElement('g:price')
            handler.startElement('g:availability', {}); handler.characters('in stock'); handler.endElement('g:availability')
            handler.startElement('g:condition', {}); handler.characters('new'); handler.endElement('g:condition')
            handler.endElement('item')
        except: continue

    handler.endElement('channel'); handler.endElement('rss')
    return HttpResponse(out.getvalue(), content_type='application/xml')

# Інші в'ю (заглушки для стабільності)
def about_view(request): return render(request, 'store/about.html')
def contacts_view(request): return render(request, 'store/contacts.html')
def delivery_payment_view(request): return render(request, 'store/delivery_payment.html')
def warranty_view(request): return render(request, 'store/warranty.html')
def faq_view(request): return render(request, 'store/faq.html')
def robots_txt(request): return HttpResponse("User-agent: *\nSitemap: https://r16.com.ua/sitemap.xml", content_type="text/plain")
def redirect_old_product_urls(request, product_id): return redirect('store:home')
def fix_product_names_view(request): return JsonResponse({'ok':True})
def sync_google_sheet_view(request): return redirect('store:home')
def bot_callback_view(request): return JsonResponse({'ok':True})
def cart_add_ajax_view(request, product_id): return JsonResponse({'ok':True})
def cart_remove_view(request, product_id): return redirect('store:cart_detail')
def cart_update_quantity_view(request, product_id): return redirect('store:cart_detail')
