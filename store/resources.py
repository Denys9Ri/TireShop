import re
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Product, Brand

# "Регулярний вираз" для розбору розміру "175/70 R13"
SIZE_REGEX = re.compile(r'(\d+)/(\d+)\s*R(\d+)')

class ProductResource(resources.ModelResource):
    # Посилання на Бренд (без змін)
    brand = fields.Field(
        column_name='Бренд',
        attribute='brand',
        widget=ForeignKeyWidget(Brand, 'name'))

    # "Віртуальні" поля (без змін)
    width = fields.Field()
    profile = fields.Field()
    diameter = fields.Field()
    
    season_mapping = {
        'зима': 'winter',
        'лето': 'summer',
        'всесез': 'all-season',
    }

    class Meta:
        model = Product
        
        # --- ГОЛОВНІ ЗМІНИ ТУТ ---
        
        # 1. "Унікальний Ключ" (Natural Key)
        # Ми кажемо, що комбінація цих 5 полів = 1 унікальний товар.
        # Імпортер буде шукати товар за цим ключем.
        import_id_fields = ('brand', 'name', 'width', 'profile', 'diameter')

        # 2. "Тільки Ціна та Наявність"
        # Ми кажемо, що при імпорті ми читаємо ТІЛЬКИ ці поля.
        # Оскільки 'photo_url' тут НЕМАЄ, імпортер його НЕ чіпатиме.
        fields = ('name', 'brand', 'width', 'profile', 'diameter', 'seasonality', 'cost_price', 'stock_quantity')
        
        # 3. Карта стовпців (ми видалили 'id' звідси)
        export_order = ('Бренд', 'Модель', 'Типоразмер', 'Сезон', 'Цена', 'Кол-во')
        skip_unchanged = True
        report_skipped = True
        
        # Назви стовпців у вашому CSV (без змін)
        map_field_name = {
            'name': 'Модель',
            'seasonality': 'Сезон',
            'cost_price': 'Цена',
            'stock_quantity': 'Кол-во',
        }

    # "Магія" для обробки стовпців (без змін)
    def before_import_row(self, row, **kwargs):
        # 1. Обробка 'Типоразмер'
        size_str = row.get('Типоразмер', '')
        match = SIZE_REGEX.search(size_str)
        if match:
            row['width'] = match.group(1)
            row['profile'] = match.group(2)
            row['diameter'] = match.group(3)
        else:
            # Якщо розмір не розпізнано, ставимо "заглушки"
            # Це важливо, щоб "унікальний ключ" не зламався
            row['width'] = 0
            row['profile'] = 0
            row['diameter'] = 0
        
        # 2. Обробка 'Сезон'
        season_str = row.get('Сезон', '').strip().lower()
        if season_str in self.season_mapping:
            row['Сезон'] = self.season_mapping[season_str]
        else:
            row['Сезон'] = 'all-season' # Заглушка, якщо сезон не вказано
            
        # 3. Обробка 'Кол-во'
        quantity_str = row.get('Кол-во', '0').strip()
        if quantity_str == '>12':
            row['Кол-во'] = 20
        elif not quantity_str.isdigit():
            row['Кол-во'] = 0
        
        # 4. Обробка 'Бренд'
        brand_name = row.get('Бренд')
        if brand_name:
            Brand.objects.get_or_create(name=brand_name)
        else:
            # Якщо бренд не вказано, це проблема для ключа
            row['Бренд'] = 'Unknown' # Ставимо "заглушку"
            Brand.objects.get_or_create(name='Unknown')
            
    # Прив'язуємо "віртуальні" поля (без змін)
    def dehydrate_width(self, product):
        return product.width
    def dehydrate_profile(self, product):
        return product.profile
    def dehydrate_diameter(self, product):
        return product.diameter
