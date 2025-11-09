from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .models import Product, Order, OrderItem, Brand
from .cart import Cart

# --- (Код для каталогу, кошика і т.д. - без змін) ---
def catalog_view(request):
    products = Product.objects.all().order_by('brand__name', 'name')
    brands = Brand.objects.all().order_by('name')
    widths = Product.objects.values_list('width', flat=True).distinct().order_by('width')
    profiles = Product.objects.values_list('profile', flat=True).distinct().order_by('profile')
    diameters = Product.objects.values_list('diameter', flat=True).distinct().order_by('diameter')
    season_choices = Product.SEASON_CHOICES
    selected_brand = request.GET.get('brand')
    selected_width = request.GET.get('width')
    selected_profile = request.GET.get('profile')
    selected_diameter = request.GET.get('diameter')
    selected_season = request.GET.get('season')
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
    context = {
        'products': products,
        'all_brands': brands,
        'all_widths': widths,
        'all_profiles': profiles,
        'all_diameters': diameters,
        'all_seasons': season_choices,
        'selected_brand': int(selected_brand) if selected_brand else None,
        'selected_width': int(selected_width) if selected_width else None,
        'selected_profile': int(selected_profile) if selected_profile else None,
        'selected_diameter': int(selected_diameter) if selected_diameter else None,
        'selected_season': selected_season,
    }
    return render(request, 'store/catalog.html', context)

def cart_detail_view(request):
    cart = Cart(request)
    return render(request, 'store/cart.html', {'cart': cart})

@require_POST
def cart_add_view(request, product_id):
    cart = Cart(request) 
    product = get_object_or_404(Product, id=product_id) 
    cart.add(product=product, quantity=1, update_quantity=False)
    return redirect(request.META.get('HTTP_REFERER', 'catalog'))

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

def cart_remove_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('store:cart_detail')

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
        if request.user.is_authenticated:
            return redirect('users:profile')
        return redirect('catalog') 
    return render(request, 'store/checkout.html', {})

# --- (Імпорти для "Акведука") ---
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
import re

SIZE_REGEX = re.compile(r'(\d+)/(\d+)\s*R(\d+)')
SEASON_MAPPING = {
    'зима': 'winter',
    'лето': 'summer',
    'всесез': 'all-season',
}

# ---
# --- ОСЬ ОНОВЛЕНИЙ "АКВЕДУК"
# ---
@staff_member_required 
def sync_google_sheet_view(request):
    
    # --- ВАШЕ ПОСИЛАННЯ ВЖЕ ТУТ ---
    GOOGLE_SHEET_URL = 'https://docs.google.com/spreadsheets/d/1lUuQ5vMPJy8IeiqKwp9dmfB1P3CnAMO-eAXK-V9dJIw/edit?usp=drivesdk'
    
    # --- Я ВИДАЛИВ "ЗЛАМАНИЙ" ЗАПОБІЖНИК (IF-блок) ---
        
    try:
        # 1. Автентифікація
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            settings.GSPREAD_CREDENTIALS_PATH, scope
        )
        client = gspread.authorize(creds)

        # 2. ВІДКРИВАЄМО ЗА ПРЯМИМ ПОСИЛАННЯМ
        sheet = client.open_by_url(GOOGLE_SHEET_URL).sheet1
        
        # 3. Отримуємо дані
        rows = sheet.get_all_records() 
        
        created_count = 0
        updated_count = 0

        # 4. "Пробігаємо" по кожному рядку
        for row in rows:
            brand_name = row.get('Бренд', '').strip()
            model_name = row.get('Модель', '').strip()
            size_str = row.get('Типоразмер', '')
            season_str = row.get('Сезон', '').strip().lower()
            price_str = row.get('Цена', '0')
            quantity_str = row.get('Кол-во', '0')
            
            if not brand_name or not model_name or not size_str:
                continue 

            # 5. "Чистимо" дані
            brand_obj, _ = Brand.objects.get_or_create(name=brand_name)
            
            width_val, profile_val, diameter_val = 0, 0, 0
            match = SIZE_REGEX.search(size_str)
            if match:
                width_val = int(match.group(1))
                profile_val = int(match.group(2))
                diameter_val = int(match.group(3))
            
            season_val = SEASON_MAPPING.get(season_str, 'all-season')
            
            try:
                price_val = float(str(price_str).replace(' ', '').replace(',', '.'))
            except ValueError:
                price_val = 0
                
            if quantity_str == '>12':
                quantity_val = 20
            elif isinstance(quantity_str, str) and not quantity_str.isdigit():
                quantity_val = 0
            else:
                try:
                    quantity_val = int(quantity_str)
                except ValueError:
                    quantity_val = 0

            # 6. Знайти або Створити
            product, created = Product.objects.update_or_create(
                brand=brand_obj,
                name=model_name,
                width=width_val,
                profile=profile_val,
                diameter=diameter_val,
                defaults={
                    'seasonality': season_val,
                    'cost_price': price_val,
                    'stock_quantity': quantity_val
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        # 7. Звіт
        messages.success(request, f"Синхронізація завершена! Створено: {created_count}. Оновлено: {updated_count}.")
        
    except Exception as e:
        messages.error(request, f"Помилка синхронізації: {e}")

    # 8. Повертаємо адміна назад
    return redirect('admin:store_product_changelist')
