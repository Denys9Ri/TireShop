from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
# Ми додали 'Brand' до списку імпорту
from .models import Product, Order, OrderItem, Brand
from .cart import Cart

# --- 1. ОНОВЛЕНИЙ КАТАЛОГ (з логікою фільтрів) ---
def catalog_view(request):
    # Починаємо з усіх товарів, сортуємо за брендом
    products = Product.objects.all().order_by('brand__name', 'name')
    
    # --- Логіка для заповнення фільтрів ---
    # Беремо тільки унікальні значення з бази
    brands = Brand.objects.all().order_by('name')
    widths = Product.objects.values_list('width', flat=True).distinct().order_by('width')
    profiles = Product.objects.values_list('profile', flat=True).distinct().order_by('profile')
    diameters = Product.objects.values_list('diameter', flat=True).distinct().order_by('diameter')
    season_choices = Product.SEASON_CHOICES

    # --- Логіка для обробки запиту фільтрації ---
    # Отримуємо вибрані значення з GET-запиту (з URL)
    selected_brand = request.GET.get('brand')
    selected_width = request.GET.get('width')
    selected_profile = request.GET.get('profile')
    selected_diameter = request.GET.get('diameter')
    selected_season = request.GET.get('season')

    # Застосовуємо фільтри, ЯКЩО вони були вибрані
    if selected_brand:
        products = products.filter(brand__id=selected_brand)
    if selected_width:
        products = products.filter(width=selected_width)
    if selected_profile:
        products = products.filter(profile=selected_profile)
    if selected_diameter:
        products = products.filter(diameter=selected_diameter)
    if selected_season:
        products = products.filter(seasonality=selected_season)

    # Збираємо всі дані, щоб відправити їх у HTML
    context = {
        'products': products,
        
        # Списки для заповнення <select> у фільтрі
        'all_brands': brands,
        'all_widths': widths,
        'all_profiles': profiles,
        'all_diameters': diameters,
        'all_seasons': season_choices,
        
        # Збережені значення, щоб фільтр "пам'ятав" вибір
        'selected_brand': int(selected_brand) if selected_brand else None,
        'selected_width': int(selected_width) if selected_width else None,
        'selected_profile': int(selected_profile) if selected_profile else None,
        'selected_diameter': int(selected_diameter) if selected_diameter else None,
        'selected_season': selected_season,
    }

    # "Малюємо" HTML-сторінку 'catalog.html', передаючи їй ВСІ ці дані
    return render(request, 'store/catalog.html', context)

# --- 2. СТОРІНКА КОШИКА (Без змін) ---
def cart_detail_view(request):
    cart = Cart(request)
    return render(request, 'store/cart.html', {'cart': cart})

# --- 3. ДОДАТИ В КОШИК (Без змін) ---
@require_POST
def cart_add_view(request, product_id):
    cart = Cart(request) 
    product = get_object_or_404(Product, id=product_id) 
    cart.add(product=product, quantity=1, update_quantity=False)
    # Повертаємо користувача на ту ж сторінку, з якої він додав товар
    # (Це краще, ніж завжди повертати в каталог)
    return redirect(request.META.get('HTTP_REFERER', 'catalog'))

# --- 4. ОНОВИТИ КІЛЬКІСТЬ (Без змін) ---
@require_POST
def cart_update_quantity_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity > 0:
        cart.add(product=product, quantity=quantity, update_quantity=True)
    else:
        cart.remove(product)
    return redirect('store:cart_detail') 

# --- 5. ВИДАЛИТИ З КОШИКА (Без змін) ---
def cart_remove_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('store:cart_detail')

# --- 6. ОФОРМЛЕННЯ ЗАМОВЛЕННЯ (Без змін) ---
def checkout_view(request):
    cart = Cart(request)
    if len(cart) == 0:
        return redirect('catalog')

    if request.method == 'POST':
        shipping_type = request.POST.get('shipping_type')
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        city = request.POST.get('city')
        nova_poshta_branch = request.POST.get('nova_poshta_branch')

        order = Order.objects.create(
            customer=request.user if request.user.is_authenticated else None,
            shipping_type=shipping_type,
            full_name=full_name,
            phone=phone,
            email=email,
            city=city,
            nova_poshta_branch=nova_poshta_branch,
            status='new'
        )

        for item in cart:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                quantity=item['quantity'],
                price_at_purchase=item['price'] 
            )
        
        cart.clear()
        
        # Тут краще створити сторінку 'order_success.html'
        # Але поки що повертаємо в кабінет (якщо залогінений) або в каталог
        if request.user.is_authenticated:
            return redirect('users:profile')
        return redirect('catalog') 

    return render(request, 'store/checkout.html', {})

# ... (всі ваші 'import' згори)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
import re

# --- "Розумний" код для розбору розміру (з нашого старого 'resources.py') ---
SIZE_REGEX = re.compile(r'(\d+)/(\d+)\s*R(\d+)')
SEASON_MAPPING = {
    'зима': 'winter',
    'лето': 'summer',
    'всесез': 'all-season',
}

# ---
# --- ОСЬ НАШ НОВИЙ "АКВЕДУК"
# ---
@staff_member_required # Доступ тільки для Адмінів
def sync_google_sheet_view(request):
    
    # --- ВАЖЛИВО: Назва Вашої Таблиці ---
    # Переконайтеся, що ваша Google Таблиця називається ТОЧНО ТАК:
    GOOGLE_SHEET_NAME = 'TireShopPrice'
    
    try:
        # 1. Автентифікація (використовуємо "Секретний Файл" з Render)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            settings.GSPREAD_CREDENTIALS_PATH, scope
        )
        client = gspread.authorize(creds)

        # 2. Відкриваємо таблицю і перший аркуш
        sheet = client.open(GOOGLE_SHEET_NAME).sheet1
        
        # 3. Отримуємо ВСІ дані (крім першого рядка заголовків)
        rows = sheet.get_all_records() # Це "читає" заголовки автоматично
        
        # Лічильники для звіту
        created_count = 0
        updated_count = 0

        # 4. "Пробігаємо" по кожному рядку з прайсу
        for row in rows:
            # Отримуємо дані (за назвами стовпців з файлу)
            brand_name = row.get('Бренд', '').strip()
            model_name = row.get('Модель', '').strip()
            size_str = row.get('Типоразмер', '')
            season_str = row.get('Сезон', '').strip().lower()
            price_str = row.get('Цена', '0')
            quantity_str = row.get('Кол-во', '0')
            
            # (Пропускаємо "порожні" рядки)
            if not brand_name or not model_name or not size_str:
                continue 

            # 5. "Чистимо" дані (той самий код, що й раніше)
            # 5.1. Бренд
            brand_obj, _ = Brand.objects.get_or_create(name=brand_name)
            
            # 5.2. Розмір
            width_val, profile_val, diameter_val = 0, 0, 0
            match = SIZE_REGEX.search(size_str)
            if match:
                width_val = int(match.group(1))
                profile_val = int(match.group(2))
                diameter_val = int(match.group(3))
            
            # 5.3. Сезон
            season_val = SEASON_MAPPING.get(season_str, 'all-season')
            
            # 5.4. Ціна
            try:
                # Видаляємо пробіли і замінюємо кому на крапку
                price_val = float(str(price_str).replace(' ', '').replace(',', '.'))
            except ValueError:
                price_val = 0
                
            # 5.5. Наявність
            if quantity_str == '>12':
                quantity_val = 20
            elif isinstance(quantity_str, str) and not quantity_str.isdigit():
                quantity_val = 0
            else:
                quantity_val = int(quantity_str)

            # 6. ГОЛОВНА КОМАНДА: Знайти (за "розумним" ключем) або Створити
            product, created = Product.objects.update_or_create(
                brand=brand_obj,
                name=model_name,
                width=width_val,
                profile=profile_val,
                diameter=diameter_val,
                # 'defaults' - це те, що ми ОНОВЛЮЄМО
                defaults={
                    'seasonality': season_val,
                    'cost_price': price_val,
                    'stock_quantity': quantity_val
                    # 'photo_url' НЕ ЧІПАЄМО!
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        # 7. Звіт
        messages.success(request, f"Синхронізація завершена! Створено: {created_count}. Оновлено: {updated_count}.")
        
    except Exception as e:
        # Якщо щось пішло не так (наприклад, "TireShopPrice" не знайдено)
        messages.error(request, f"Помилка синхронізації: {e}")

    # 8. Повертаємо адміна назад на сторінку "Products"
    return redirect('admin:store_product_changelist')

