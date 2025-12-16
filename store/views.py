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

# --- 🧠 SEO ШАБЛОНИ (HTML) ---
SEO_TEMPLATES = {
    'winter': {
        'h2': "Чому варто купити зимові шини {brand} {size}?",
        'text': """
            <p>Зимова гума <b>{brand}</b> {size} розроблена спеціально для складних погодних умов України. 
            Завдяки особливому складу компаунду, ці шини залишаються еластичними навіть при сильних морозах.</p>
            <ul>
                <li>✅ <b>Відмінне зчеплення:</b> Глибокий протектор та ламелі забезпечують контроль на снігу та льоду.</li>
                <li>✅ <b>Безпека:</b> Скорочений гальмівний шлях на слизькій дорозі.</li>
                <li>✅ <b>Комфорт:</b> {brand} гарантує м'якість ходу та низький рівень шуму.</li>
            </ul>
            <p>Якщо ви шукаєте надійні зимові колеса, модельний ряд {brand} — це ідеальний вибір для вашого авто.</p>
        """,
        'faq_best': "Які зимові шини {brand} найкращі?",
        'faq_best_ans': "Найпопулярніші зимові моделі {brand} забезпечують максимальну безпеку. Рекомендуємо звернути увагу на шини з направленим малюнком протектора."
    },
    'summer': {
        'h2': "Літні шини {brand} {size}: Швидкість та контроль",
        'text': """
            <p>Літня гума <b>{brand}</b> {size} створена для динамічної їзди та максимального комфорту в теплу пору року.
            Жорсткі боковини та продумана дренажна система захищають від аквапланування.</p>
            <ul>
                <li>☀️ <b>Термостійкість:</b> Гума не «пливе» на розпеченому асфальті.</li>
                <li>🌧 <b>Захист від дощу:</b> Ефективні канавки миттєво відводять воду з плями контакту.</li>
                <li>🚀 <b>Економічність:</b> Знижений опір коченню допомагає економити пальне.</li>
            </ul>
            <p>Обираючи літні шини {brand}, ви отримуєте керованість спортивного рівня та довговічність.</p>
        """,
        'faq_best': "Які літні моделі {brand} найтіхіші?",
        'faq_best_ans': "Лінійка літніх шин {brand} вирізняється акустичним комфортом. Спеціальний малюнок протектора мінімізує шум навіть на високих швидкостях."
    },
    'all_season': {
        'h2': "Всесезонні шини {brand} {size}: Універсальність на весь рік",
        'text': """
            <p>Бажаєте заощадити на перевзуванні? Всесезонна гума <b>{brand}</b> {size} — це компроміс, який працює.
            Вона поєднує характеристики зимових та літніх шин, забезпечуючи стабільність у міжсезоння.</p>
            <p>Це ідеальний варіант для м'якої зими та міського циклу їзди. Шини {brand} мають маркування M+S.</p>
        """,
        'faq_best': "Чи підходять всесезонні шини {brand} для зими?",
        'faq_best_ans': "Так, всесезонні моделі {brand} розраховані на м'яку європейську зиму. Проте для глибокого снігу та ожеледиці ми рекомендуємо повноцінну зимову гуму."
    },
    'default': {
        'h2': "Купити шини {brand} {size} в Києві",
        'text': """
            <p>Інтернет-магазин R16 пропонує широкий вибір шин <b>{brand}</b>. 
            Ми є офіційним партнером багатьох брендів, тому гарантуємо якість та найнижчі ціни.</p>
            <p>Замовляйте гуму {size} з доставкою Новою Поштою або забирайте самовивозом у Києві (вул. Володимира Качали, 3).</p>
        """,
        'faq_best': "Який бренд шин обрати?",
        'faq_best_ans': "Вибір залежить від вашого бюджету та стилю їзди. {brand} — це чудовий вибір у категорії 'ціна/якість'."
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
    # Захист від пустої бази: повертаємо QuerySet навіть якщо пустий
    return Product.objects.filter(width__gt=0, diameter__gt=0).annotate(
        status_order=Case(When(stock_quantity__gt=0, then=Value(0)), default=Value(1), output_field=IntegerField())
    )

def generate_seo_content(brand_obj=None, season_db=None, w=None, p=None, d=None, min_price=0, max_price=0):
    brand_name = brand_obj.name if brand_obj else "Всі бренди"
    size_str = f"{w}/{p} R{d}" if (w and p and d) else ""
    
    key = season_db if season_db in SEO_TEMPLATES else 'default'
    template = SEO_TEMPLATES[key]

    # Формування H1
    h1_parts = []
    if season_db == 'winter': h1_parts.append("Зимові шини")
    elif season_db == 'summer': h1_parts.append("Літні шини")
    elif season_db == 'all_season': h1_parts.append("Всесезонні шини")
    else: h1_parts.append("Шини")
    
    if brand_obj: h1_parts.append(brand_obj.name)
    if size_str: h1_parts.append(size_str)
    
    h1_final = " ".join(h1_parts)
    title_final = f"{h1_final} — Ціна від {min_price} грн | R16.com.ua"
    
    # Формування Тексту
    try:
        description_html = template['text'].format(brand=brand_name, size=size_str)
        seo_h2 = template['h2'].format(brand=brand_name, size=size_str)
    except:
        description_html = SEO_TEMPLATES['default']['text'].format(brand=brand_name, size=size_str)
        seo_h2 = h1_final

    meta_desc = f"{h1_final} в наявності! 💰 Ціна: {min_price}-{max_price} грн. 🚚 Доставка по Україні. Гарантія якості."

    return {
        'title': title_final,
        'h1': h1_final,
        'seo_h2': seo_h2,
        'description_html': description_html,
        'meta_description': meta_desc,
        'faq_key': key,
        'brand_name': brand_name
    }

def get_faq_schema(seo_data, min_price):
    key = seo_data['faq_key']
    template = SEO_TEMPLATES[key]
    brand = seo_data['brand_name']
    h1 = seo_data['h1']

    try:
        q_best = template['faq_best'].format(brand=brand)
        a_best = template['faq_best_ans'].format(brand=brand)
    except:
        q_best = f"Чому обирають {brand}?"
        a_best = "Це надійний вибір."

    faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f"💰 Яка ціна на {h1}?",
                "acceptedAnswer": {"@type": "Answer", "text": f"Ціни починаються від {min_price} грн. Актуальна вартість залежить від розміру."}
            },
            {
                "@type": "Question",
                "name": q_best,
                "acceptedAnswer": {"@type": "Answer", "text": a_best}
            },
            {
                "@type": "Question",
                "name": "🚚 Чи є доставка?",
                "acceptedAnswer": {"@type": "Answer", "text": "Так! Самовивіз у Києві (Відрадний). Доставка Новою Поштою по Україні."}
            }
        ]
    }
    return json.dumps(faq)

def get_cross_links(current_season_slug, current_brand, w, p, d):
    links = []
    # 1. Популярні розміри
    if current_season_slug and not w:
        top_sizes = [(175,70,13), (185,65,14), (195,65,15), (205,55,16), (215,60,16), (225,45,17), (235,55,18)]
        group = {'title': 'Популярні розміри:', 'items': []}
        for sw, sp, sd in top_sizes:
            url = reverse('store:seo_season_size', args=[current_season_slug, sw, sp, sd])
            group['items'].append({'text': f"R{sd} {sw}/{sp}", 'url': url})
        links.append(group)

    # 2. Інші бренди в цьому розмірі
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
            
    # 3. Інші сезони цього бренду
    if current_brand:
        group = {'title': f'Інші сезони {current_brand.name}:', 'items': []}
        for slug, info in SEASONS_MAP.items():
            if slug != current_season_slug:
                url = reverse('store:seo_brand_season', args=[current_brand.name, slug])
                group['items'].append({'text': info['ua'], 'url': url})
        links.append(group)
    return links

# --- 🔥 ГОЛОВНИЙ КОНТРОЛЕР (SEO MATRIX) 🔥 ---
def seo_matrix_view(request, slug=None, brand_slug=None, season_slug=None, width=None, profile=None, diameter=None):
    products = get_base_products()
    brand_obj = None
    season_db = None

    # === ЛОГІКА РОЗПІЗНАВАННЯ (Fix 500 Error для хлібних крихт) ===
    # Якщо прийшов параметр 'slug' (з універсального шляху), ми маємо вгадати, що це.
    if slug:
        if slug in SEASONS_MAP:
            season_slug = slug
        else:
            # Спробуємо знайти бренд
            brand_obj = Brand.objects.filter(name__iexact=slug).first()
            if brand_obj:
                brand_slug = slug
            else:
                # Якщо нічого не знайдено, не падаємо, а просто показуємо каталог
                pass 

    # === ФІЛЬТРАЦІЯ ===
    if brand_obj:
        products = products.filter(brand=brand_obj)
    elif brand_slug: 
        brand_obj = Brand.objects.filter(name__iexact=brand_slug).first()
        if brand_obj: products = products.filter(brand=brand_obj)

    if season_slug and season_slug in SEASONS_MAP:
        season_db = SEASONS_MAP[season_slug]['db']
        products = products.filter(seasonality=season_db)

    if width and profile and diameter:
        products = products.filter(width=width, profile=profile, diameter=diameter)

    # === СТАТИСТИКА (Безпечна) ===
    stats = products.aggregate(min_price=Min('price'), max_price=Max('price'), count=Count('id'))
    min_price = stats['min_price'] if stats['min_price'] is not None else 0
    max_price = stats['max_price'] if stats['max_price'] is not None else 0
    prod_count = stats['count']

    # === ГЕНЕРАЦІЯ КОНТЕНТУ ===
    seo_data = generate_seo_content(brand_obj, season_db, width, profile, diameter, int(min_price), int(max_price))
    faq_schema = get_faq_schema(seo_data, int(min_price))
    cross_links = get_cross_links(season_slug, brand_obj, width, profile, diameter)

    # === ВІДОБРАЖЕННЯ ===
    brands = Brand.objects.all().order_by('name')
    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'store/catalog.html', {
        'page_obj': page_obj, 
        'all_brands': brands,
        'all_widths': Product.objects.filter(width__gt=0).values_list('width', flat=True).distinct().order_by('width'),
        'all_profiles': Product.objects.filter(profile__gt=0).values_list('profile', flat=True).distinct().order_by('profile'),
        'all_diameters': Product.objects.filter(diameter__gt=0).values_list('diameter', flat=True).distinct().order_by('diameter'),
        'all_seasons': Product.SEASON_CHOICES,
        
        'selected_brand_id': brand_obj.id if brand_obj else None,
        'selected_season': season_db,
        'selected_width': width, 'selected_profile': profile, 'selected_diameter': diameter,
        
        'seo_title': seo_data['title'],
        'seo_h1': seo_data['h1'],
        'seo_h2': seo_data['seo_h2'],
        'seo_description': seo_data['meta_description'],
        'seo_text_html': seo_data['description_html'],
        'faq_schema': faq_schema,
        'cross_links': cross_links,
        'is_seo_page': True
    })

# --- ЗВИЧАЙНИЙ ПОШУК ---
def catalog_view(request):
    # Перенаправляємо на SEO Matrix, щоб використовувати ту саму логіку
    return seo_matrix_view(request)

# --- СТОРІНКА ТОВАРУ (ОНОВЛЕНА) ---
def product_detail_view(request, slug):
    product = get_object_or_404(Product, slug=slug)
    similar = Product.objects.filter(width=product.width, diameter=product.diameter).exclude(id=product.id)[:4]
    
    # Генеруємо контент для товару
    seo_data = generate_seo_content(
        brand_obj=product.brand,
        season_db=product.seasonality,
        w=product.width, 
        p=product.profile, 
        d=product.diameter,
        min_price=product.price,
        max_price=product.price
    )
    faq_schema = get_faq_schema(seo_data, int(product.price))

    # Правильна хлібна крихта (використовує універсальний шлях)
    parent_category = None
    for k, v in SEASONS_MAP.items():
        if v['db'] == product.seasonality:
            # reverse('store:seo_universal', args=['zymovi'])
            parent_category = {'name': v['ua'], 'url': reverse('store:seo_universal', args=[k])}
            break

    return render(request, 'store/product_detail.html', {
        'product': product, 
        'similar_products': similar, 
        'parent_category': parent_category,
        'seo_title': seo_data['title'], 
        'seo_h1': seo_data['h1'], 
        'seo_h2': seo_data['seo_h2'],
        'seo_text_html': seo_data['description_html'], 
        'faq_schema': faq_schema
    })

# --- РЕДИРЕКТ СТАРИХ ID ---
def redirect_old_product_urls(request, product_id):
    p = get_object_or_404(Product, id=product_id)
    return redirect('store:product_detail', slug=p.slug, permanent=True)

# --- ФУНКЦІОНАЛ (КОШИК, ЗАМОВЛЕННЯ) ---
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

def checkout_view(request):
    cart = Cart(request)
    if not cart: return redirect('store:catalog')
    
    if request.method == 'POST':
        is_pickup = request.POST.get('shipping_type') == 'pickup'
        
        # Створюємо замовлення
        order = Order.objects.create(
            customer=request.user if request.user.is_authenticated else None,
            shipping_type=request.POST.get('shipping_type'),
            full_name=request.POST.get('pickup_name' if is_pickup else 'full_name'),
            phone=request.POST.get('pickup_phone' if is_pickup else 'phone'),
            email=None if is_pickup else request.POST.get('email'),
            city="Київ, Самовивіз" if is_pickup else request.POST.get('city'),
            nova_poshta_branch=None if is_pickup else request.POST.get('nova_poshta_branch')
        )

        # Товари
        items_text = ""
        for item in cart:
            p = item['product']
            OrderItem.objects.create(order=order, product=p, quantity=item['quantity'], price_at_purchase=item['price'])
            items_text += f"\n🔘 {p.brand.name} {p.name} ({p.width}/{p.profile} R{p.diameter}) — {item['quantity']} шт."

        # Доставка для Телеграм
        delivery_info = "🏃 <b>САМОВИВІЗ</b> (Київ)"
        if not is_pickup:
            city = request.POST.get('city', '-')
            branch = request.POST.get('nova_poshta_branch', '-')
            delivery_info = f"🚚 <b>НОВА ПОШТА</b>\n📍 Місто: {city}\n🏢 Відділення: {branch}"

        # Повідомлення
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

# --- ІНФО ---
def about_view(request): return render(request, 'store/about.html')
def contacts_view(request): return render(request, 'store/contacts.html')
def delivery_payment_view(request): return render(request, 'store/delivery_payment.html')
def warranty_view(request): return render(request, 'store/warranty.html')

# --- БОТ ---
@require_POST
def bot_callback_view(request):
    try:
        data = json.loads(request.body)
        phone = data.get('phone')
        if phone:
            send_telegram(f"🆘 <b>SOS ЗАПИТ (ЧАТ-БОТ)</b>\n📞 Телефон: {phone}\n⚠️ Клієнт просить допомоги з підбором!")
            return JsonResponse({'status': 'ok'})
    except Exception as e:
        print(f"Bot Error: {e}")
    return JsonResponse({'status': 'error'}, status=400)

@transaction.atomic
def sync_google_sheet_view(request): return redirect('admin:store_product_changelist')
