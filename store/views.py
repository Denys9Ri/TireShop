from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Case, When, Value, IntegerField
# Імпорт транзакцій для економії пам'яті
from django.db import transaction 

from .models import Product, Order, OrderItem, Brand
from .cart import Cart
from users.models import UserProfile

# --- 1. КАТАЛОГ (З правильним сортуванням) ---
def catalog_view(request):
    # Оптимізація: values_list легший за objects.all()
    brands = Brand.objects.all().order_by('name')
    widths = Product.objects.values_list('width', flat=True).distinct().order_by('width')
    profiles = Product.objects.values_list('profile', flat=True).distinct().order_by('profile')
    diameters = Product.objects.values_list('diameter', flat=True).distinct().order_by('diameter')
    season_choices = Product.SEASON_CHOICES
    
    # Створюємо віртуальний порядок: Є в наявності (0) -> Немає (1)
    products = Product.objects.annotate(
        status_order=Case(
            When(stock_quantity__gt=0, then=Value(0)), 
            default=Value(1),
            output_field=IntegerField(),
        )
    )

    # Фільтрація
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
    
    # Сортування: Спочатку наявність, потім Бренд, потім Назва
    products = products.order_by('status_order', 'brand__name', 'name')
    
    # Пагінація (12 товарів на сторінку)
    paginator = Paginator(products, 12) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number) 

    # Збереження фільтрів при переході по сторінках
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    filter_query_string = query_params.urlencode()

    context = {
        'page_obj': page_obj,
        'filter_query_string': filter_query_string,
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


def product_detail_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'store/product_detail.html', {'product': product})


def contacts_view(request):
    return render(request, 'store/contacts.html')


def delivery_payment_view(request):
    return render(request, 'store/delivery_payment.html')

# -----------------------------------------------------------------
# КОШИК (Без змін)
# -----------------------------------------------------------------

def cart_detail_view(request):
    cart = Cart(request)
    return render(request, 'store/cart.html', {'cart': cart})

@require_POST
def cart_add_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = 1
    quantity = max(1, quantity)
    cart.add(product=product, quantity=quantity, update_quantity=False)
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

    profile = None
    prefill = {}
    if request.user.is_authenticated:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        prefill = {
            'full_name': f"{request.user.last_name} {request.user.first_name}".strip(),
            'email': request.user.email,
            'phone': profile.phone_primary,
            'city': profile.city,
            'nova_poshta_branch': profile.nova_poshta_branch,
            'pickup_name': f"{request.user.first_name} {request.user.last_name}".strip(),
            'pickup_phone': profile.phone_primary,
        }

    if request.method == 'POST':
        shipping_type = request.POST.get('shipping_type')
        is_pickup = shipping_type == 'pickup'
        full_name = request.POST.get('pickup_name') if is_pickup else request.POST.get('full_name')
        phone = request.POST.get('pickup_phone') if is_pickup else request.POST.get('phone')
        email = None if is_pickup else request.POST.get('email')
        city = "Київ, вул. Володимира Качали, 3" if is_pickup else request.POST.get('city')
        nova_poshta_branch = None if is_pickup else request.POST.get('nova_poshta_branch')
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

        if request.user.is_authenticated and profile:
            if phone:
                profile.phone_primary = phone
            if not is_pickup:
                if city:
                    profile.city = city
                if nova_poshta_branch:
                    profile.nova_poshta_branch = nova_poshta_branch
            profile.save()

        if request.user.is_authenticated:
            return redirect('users:profile')
        return redirect('catalog')
    return render(request, 'store/checkout.html', {'prefill': prefill})

# -----------------------------------------------------------------
# АКВЕДУК (GOOGLE SHEETS) - ОПТИМІЗОВАНИЙ
# -----------------------------------------------------------------
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
import re 

SIZE_REGEX = re.compile(r'(\d+)/(\d+)\s*R(\d+)')
SEASON_MAPPING = {
    'winter': ('зим', 'зима', 'зимн', 'зимова', 'winter'),
    'summer': ('лет', 'лето', 'літ', 'літо', 'summer'),
    'all-season': ('всесез', 'всесезон', 'all-season'),
}

def normalize_season(season_raw: str) -> str:
    season_str = (season_raw or '').strip().lower()
    for normalized, prefixes in SEASON_MAPPING.items():
        for prefix in prefixes:
            if season_str.startswith(prefix):
                return normalized
    return 'all-season'

def parse_int_from_string(s):
    cleaned_s = re.sub(r'[^\d]', '', str(s))
    if cleaned_s:
        try:
            return int(cleaned_s)
        except ValueError:
            return 0
    return 0

@staff_member_required
@transaction.atomic # <--- ЦЕ "МАГІЯ", ЯКА ЕКОНОМИТЬ ПАМ'ЯТЬ
def sync_google_sheet_view(request):
    GOOGLE_SHEET_URL = 'https://docs.google.com/spreadsheets/d/1lUuQ5vMPJy8IeiqKwp9dmfB1P3CnAMO-eAXK-V9dJIw/edit?usp=drivesdk'
        
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            settings.GSPREAD_CREDENTIALS_PATH, scope
        )
        client = gspread.authorize(creds)

        try:
            sheet = client.open_by_url(GOOGLE_SHEET_URL).worksheet("Sheet1")
        except gspread.exceptions.WorksheetNotFound:
            messages.error(request, 'Помилка: Не можу знайти аркуш "Sheet1".')
            return redirect('admin:store_product_changelist')
        
        # Отримуємо дані
        all_data = sheet.get_all_values()
        if not all_data or len(all_data) < 2: 
            messages.error(request, "Помилка: Таблиця порожня.")
            return redirect('admin:store_product_changelist')

        header_row = [h.strip() for h in all_data[0]]
        data_rows = all_data[1:]

        try:
            col_map = {
                'brand': header_row.index('Бренд'),
                'model': header_row.index('Модель'),
                'size': header_row.index('Типоразмер'),
                'season': header_row.index('Сезон'),
                'price': header_row.index('Цена'),
                'quantity': header_row.index('Кол-во'),
            }
        except ValueError as e:
            messages.error(request, f"Помилка колонок: {e}")
            return redirect('admin:store_product_changelist')

        created_count = 0
        updated_count = 0

        # Попередньо завантажуємо всі бренди в пам'ять, щоб не смикати базу кожен раз
        # Це дуже прискорює роботу
        existing_brands = {b.name: b for b in Brand.objects.all()}

        for row in data_rows:
            if not any(row): continue
            
            brand_name = row[col_map['brand']].strip()
            model_name = row[col_map['model']].strip()
            size_str = row[col_map['size']].strip()
            
            if not brand_name or not model_name or not size_str: continue 

            # Оптимізований пошук бренду
            if brand_name in existing_brands:
                brand_obj = existing_brands[brand_name]
            else:
                brand_obj = Brand.objects.create(name=brand_name)
                existing_brands[brand_name] = brand_obj
            
            width_val, profile_val, diameter_val = 0, 0, 0
            match = SIZE_REGEX.search(size_str)
            if match:
                width_val = int(match.group(1))
                profile_val = int(match.group(2))
                diameter_val = int(match.group(3))
            
            season_str = row[col_map['season']].strip().lower()
            season_val = normalize_season(season_str)
            
            price_str = row[col_map['price']]
            try:
                price_val = float(str(price_str).replace(' ', '').replace(',', '.'))
            except ValueError:
                price_val = 0
                
            quantity_str = str(row[col_map['quantity']]).strip()
            quantity_val = parse_int_from_string(quantity_str)

            unique_model_name = model_name
            if not match and size_str:
                 unique_model_name = f"{model_name} [{size_str}]"

            product, created = Product.objects.update_or_create(
                brand=brand_obj,
                name=unique_model_name,
                width=width_val,
                profile=profile_val,
                diameter=diameter_val,
                defaults={
                    'seasonality': season_val,
                    'cost_price': price_val,
                    'stock_quantity': quantity_val
                }
            )
            if created: created_count += 1
            else: updated_count += 1
        
        messages.success(request, f"Синхронізація: +{created_count} нових, ↻{updated_count} оновлено.")
        
    except Exception as e:
        messages.error(request, f"Помилка: {e}")

    return redirect('admin:store_product_changelist')
