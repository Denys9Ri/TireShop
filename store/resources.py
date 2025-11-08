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

    width = fields.Field(column_name='width') # Ми створюємо "віртуальні" стовпці
    profile = fields.Field(column_name='profile')
    diameter = fields.Field(column_name='diameter')
    
    season_mapping = {
        'зима': 'winter',
        'лето': 'summer',
        'всесез': 'all-season',
    }

    class Meta:
        model = Product
        
        # --- ОСЬ ГОЛОВНЕ ВИРІШЕННЯ (Помилка 1) ---
        # Ми кажемо імпортеру пропустити перші 7 "сміттєвих" рядків.
        skip_rows = 7
        
        # Ми кажемо, що "унікальний ключ" - це 3 стовпці з CSV
        import_id_fields = ('Бренд', 'Модель', 'Типоразмер') 
        
        # --- (Решта коду з минулого разу) ---
        fields = ('name', 'brand', 'width', 'profile', 'diameter', 'seasonality', 'cost_price', 'stock_quantity')
        export_order = ('Бренд', 'Модель', 'Типоразмер', 'Сезон', 'Цена', 'Кол-во')
        skip_unchanged = True
        report_skipped = True
        
        map_field_name = {
            'name': 'Модель',
            'seasonality': 'Сезон',
            'cost_price': 'Цена',
            'stock_quantity': 'Кол-во',
        }
        
    # "Магія" для обробки стовпців (без змін)
    def before_import_row(self, row, **kwargs):
        size_str = row.get('Типоразмер', '')
        match = SIZE_REGEX.search(size_str)
        if match:
            row['width'] = match.group(1)
            row['profile'] = match.group(2)
            row['diameter'] = match.group(3)
        # (Якщо 'match' не знайдено, 'width' і т.д. будуть 'None', 
        # але Крок 2 зараз це виправить у базі даних)
        
        season_str = row.get('Сезон', '').strip().lower()
        if season_str in self.season_mapping:
            row['Сезон'] = self.season_mapping[season_str]
            
        quantity_str = row.get('Кол-во', '0').strip()
        if quantity_str == '>12':
            row['Кол-во'] = 20
        elif not quantity_str.isdigit():
            row['Кол-во'] = 0
        
        brand_name = row.get('Бренд')
        if brand_name:
            Brand.objects.get_or_create(name=brand_name)
        else:
            row['Бренд'] = 'Unknown' 
            Brand.objects.get_or_create(name='Unknown')
            
    def dehydrate_width(self, product):
        return product.width
    def dehydrate_profile(self, product):
        return product.profile
    def dehydrate_diameter(self, product):
        return product.diameter
