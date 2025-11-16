import re
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Product, Brand

SIZE_REGEX = re.compile(r'(\d+)/(\d+)\s*R(\d+)')

class ProductResource(resources.ModelResource):
    brand = fields.Field(
        column_name='Бренд',
        attribute='brand',
        widget=ForeignKeyWidget(Brand, 'name'))
    
    # Ми явно прив'язуємо 'name' до 'Модель'
    name = fields.Field(
        column_name='Модель',
        attribute='name')

    # "Віртуальні" поля (ми їх створюємо, але не чіпаємо)
    width = fields.Field()
    profile = fields.Field()
    diameter = fields.Field()
    
    season_mapping = {
        'зима': 'winter',
        'зим': 'winter',
        'winter': 'winter',
        'літо': 'summer',
        'лето': 'summer',
        'літ': 'summer',
        'summer': 'summer',
        'всесез': 'all-season',
        'всесезон': 'all-season',
        'all-season': 'all-season',
    }

    class Meta:
        model = Product
        
        # --- ФІКС 1: "Розумний" ключ (використовуємо імена з CSV) ---
        import_id_fields = ('Бренд', 'Модель', 'Типоразмер') 
        
        # --- ФІКС 2: Повертаємо "детектор BOM" ---
        from_encoding = 'utf-8-sig'
        
        # --- ФІКС 3: Повертаємо "режим поблажливості" ---
        skip_diff = True
        
        # (Ми прибрали 'skip_rows', бо файл "чистий")
        
        fields = ('name', 'brand', 'width', 'profile', 'diameter', 'seasonality', 'cost_price', 'stock_quantity')
        export_order = ('Бренд', 'Модель', 'Типоразмер', 'Сезон', 'Цена', 'Кол-во')
        report_skipped = True
        skip_unchanged = True
        
        map_field_name = {
            'name': 'Модель',
            'seasonality': 'Сезон',
            'cost_price': 'Цена',
            'stock_quantity': 'Кол-во',
        }
        
    # "Магія" для обробки стовпців
    def before_import_row(self, row, **kwargs):
        size_str = ''
        for size_key in ('Типоразмер', 'Типорозмір', 'Типоразмер '):
            size_str = row.get(size_key, '')
            if size_str:
                row['Типоразмер'] = size_str
                break
        if size_str:
            match = SIZE_REGEX.search(size_str)
            if match:
                row['width'] = match.group(1)
                row['profile'] = match.group(2)
                row['diameter'] = match.group(3)

        season_str = row.get('Сезон', '').strip().lower()
        for key, value in self.season_mapping.items():
            if season_str.startswith(key):
                row['Сезон'] = value
                break
            
        quantity_str = row.get('Кол-во', '0').strip()
        if quantity_str == '>12':
            row['Кол-во'] = 20
        elif not quantity_str.isdigit():
            row['Кол-во'] = 0
        
        brand_name = row.get('Бренд')
        if brand_name:
            brand_name = brand_name.strip().replace('“', '').replace('”', '')
            if brand_name:
                row['Бренд'] = brand_name
                Brand.objects.get_or_create(name=brand_name)
            else:
                row['Бренд'] = 'Unknown'
                Brand.objects.get_or_create(name='Unknown')
        else:
            row['Бренд'] = 'Unknown' 
            Brand.objects.get_or_create(name='Unknown')
            
    # Прив'язуємо "віртуальні" поля
    def dehydrate_width(self, product):
        return product.width
    def dehydrate_profile(self, product):
        return product.profile
    def dehydrate_diameter(self, product):
        return product.diameter
