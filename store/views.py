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
    # Список популярних розмірів для генерації кнопок
    top_sizes = [
        (175, 70, 13), (185, 65, 14), (185, 65, 15), 
        (195, 65, 15), (205, 55, 16), (215, 60, 16), 
        (225, 45, 17), (225, 50, 17), (235, 55, 18)
    ]
    
    # Показуємо кнопки, тільки якщо розмір ще НЕ обраний (щоб не захламляти екран)
    if not w:
        group = {'title': 'Популярні розміри:', 'items': []}
        for sw, sp, sd in top_sizes:
            text = f"R{sd} {sw}/{sp}"
            
            # 🔥 ЛОГІКА ПОБУДОВИ ПРАВИЛЬНОГО URL 🔥
            if current_brand and current_season_slug:
                # Якщо обрано І БРЕНД, І СЕЗОН -> ведемо на повний шлях
                url = reverse('store:seo_full', args=[current_brand.slug, current_season_slug, sw, sp, sd])
                
            elif current_season_slug:
                # Якщо обрано тільки СЕЗОН -> ведемо на сезон+розмір
                url = reverse('store:seo_season_size', args=[current_season_slug, sw, sp, sd])
                
            else:
                # Якщо ми на ГОЛОВНІЙ (нічого не обрано) або тільки Бренд -> ведемо на чистий розмір
                # (Це універсальний варіант, який завжди працює)
                url = reverse('store:seo_size', args=[sw, sp, sd])
            
            group['items'].append({'text': text, 'url': url})
        
        if group['items']:
            links.append(group)
            
    return links

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

    # 2. 🔥 ОБРОБКА ПОШУКУ 🔥
    query = request.GET.get('query', '').strip()
    if query:
        clean = re.sub(r'[/\sR\-]', '', query, flags=re.IGNORECASE)
        match = re.fullmatch(r'(\d{6,7})', clean)
        if match:
            d = match.group(1)
            products = products.filter(width=int(d[:3]), profile=int(d[3:5]), diameter=int(d[5:]))
        else:
            products = products.filter(Q(name__icontains=query) | Q(brand__name__icontains=query))

    # 3. 🔥 ОБРОБКА ФІЛЬТРІВ 🔥
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

    # --- СТАТИСТИКА (Ігноруємо ціну 0) ---
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
    faq_schema = get_faq_schema(seo_data, int(min_price))
    cross_links = get_cross_links(season_slug, brand_obj, w_int, p_int, d_int)

    # --- СОРТУВАННЯ ---
    ordering = request.GET.get('ordering')
    if ordering == 'cheap': products = products.order_by('price')
    elif ordering == 'expensive': products = products.order_by('-price')
    else: products = products.order_by('status_order', 'brand__name', 'name')

    # --- UI ---
    brands = Brand.objects.all().order_by('name')
    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    
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

def catalog_view(request): return seo_matrix_view(request)

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
    
    try:
        quantity_to_add = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity_to_add = 1
    
    # 🔥 ПЕРЕВІРКА СКЛАДУ 🔥
    # 1. Дивимось, скільки вже лежить у кошику
    cart_item = cart.cart.get(str(product.id))
    current_in_cart = cart_item['quantity'] if cart_item else 0
    
    # 2. Рахуємо, скільки вийде разом
    total_wanted = current_in_cart + quantity_to_add
    
    # 3. Якщо клієнт хоче більше, ніж є на складі -> обрізаємо
    if total_wanted > product.stock_quantity:
        # Додаємо тільки різницю, яка ще доступна
        quantity_to_add = product.stock_quantity - current_in_cart
        
        # Якщо в кошику ВЖЕ лежить максимум, то додаємо 0
        if quantity_to_add < 0:
            quantity_to_add = 0

    # Додаємо (якщо є що додавати)
    if quantity_to_add > 0:
        cart.add(product=product, quantity=quantity_to_add, update_quantity=False)
    
    # Рендеримо шматочок HTML для шторки
    html = render_to_string('store/includes/cart_offcanvas.html', {'cart': cart}, request=request)
    
    return JsonResponse({
        'html': html,
        'cart_len': len(cart)
    })

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

        # Телеграм
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

    # 🔥 АВТОЗАПОВНЕННЯ ПОЛІВ (БЕЗПЕЧНА ВЕРСІЯ) 🔥
    initial_data = {}
    if request.user.is_authenticated:
        initial_data['email'] = request.user.email
        initial_data['full_name'] = f"{request.user.first_name} {request.user.last_name}".strip()
        
        # Перевіряємо, чи є профіль, щоб не було помилок
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            initial_data['phone'] = getattr(profile, 'phone', getattr(profile, 'phone_number', ''))
            initial_data['city'] = getattr(profile, 'city', '')
            initial_data['nova_poshta_branch'] = getattr(profile, 'nova_poshta_branch', '')
            
            if not initial_data['full_name']:
                 initial_data['full_name'] = getattr(profile, 'full_name', '')

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
    """
    Секретна в'юшка для очистки назв. 
    Логіка: Залишаємо ТІЛЬКИ Модель та Індекс (без розміру).
    Використання: /secret-fix-names/?page=1, потім ?page=2 і т.д.
    """
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Тільки для адміна'})

    from .models import Product
    import re

    # 1. Налаштування пагінації (300 шт за раз)
    batch_size = 300
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        page = 1

    start_index = (page - 1) * batch_size
    end_index = start_index + batch_size

    # 2. Отримуємо порцію товарів
    products = Product.objects.order_by('id')[start_index:end_index]

    if not products:
        return JsonResponse({
            'status': 'done', 
            'message': '🎉 Всі товари перевірено! Кінець бази даних.'
        })

    count = 0
    log = []
    
    # 3. Обробка
    for p in products:
        raw_name = p.name
        
        # --- ЛОГІКА ОЧИСТКИ ---
        clean_name = raw_name.replace("Шина", "").replace("шина", "")
        
        if p.brand:
            # Видаляємо бренд з початку (щоб не було "Aplus Aplus...")
            clean_name = re.sub(f"^{p.brand.name}", "", clean_name, flags=re.IGNORECASE)
            clean_name = re.sub(f"\({p.brand.name}\)", "", clean_name, flags=re.IGNORECASE)

        # Шукаємо Індекс (наприклад 91T)
        index_match = re.search(r'\b(\d{2,3}[A-Z]{1,2})\b', clean_name)
        load_speed_idx = ""
        if index_match:
            load_speed_idx = index_match.group(1)
        
        # Видаляємо сам розмір з назви (наприклад 195/65R15)
        clean_name_no_size = re.sub(r'\d{3}/\d{2}[R|Z]\d{2}', '', clean_name)
        
        # Видаляємо знайдений індекс з тексту моделі (щоб додати його в кінці красиво)
        if load_speed_idx:
            clean_name_no_size = clean_name_no_size.replace(load_speed_idx, "")

        # Чистимо модель від сміття
        model_name = clean_name_no_size.strip()
        model_name = re.sub(r'^\W+|\W+$', '', model_name) # прибираємо коми/тире на краях

        # 🔥 ГОЛОВНА ЗМІНА: Формуємо назву БЕЗ розміру
        # Було: final_name = f"{model_name} {size_str}"
        # Стало:
        final_name = model_name
        
        if load_speed_idx:
            final_name += f" {load_speed_idx}"
        
        # Прибираємо подвійні пробіли
        final_name = re.sub(r'\s+', ' ', final_name).strip()
        # ----------------------------------

        # Зберігаємо, якщо назва змінилась і не стала пустою
        if final_name != p.name and len(final_name) > 1:
            log.append(f"{p.id}: {p.name} -> {final_name}")
            p.name = final_name
            p.save()
            count += 1
            
    # 4. Формуємо лінк на наступну сторінку
    next_page = page + 1
    next_link = f"{request.path}?page={next_page}"
    
    return JsonResponse({
        'status': 'processing',
        'current_page': page,
        'checked_range': f"{start_index} - {end_index}",
        'fixed_in_this_batch': count,
        'NEXT_STEP': f"Перейдіть сюди: {next_link}",
        'log': log[:20]
    })
