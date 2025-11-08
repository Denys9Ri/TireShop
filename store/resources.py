import re
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Product, Brand

# "Регулярний вираз" для розбору розміру "175/70 R13"
SIZE_REGEX = re.compile(r'(\d+)/(\d+)\s*R(\d+)')

class ProductResource(resources.ModelResource):
    # Кажемо імпортеру, що 'Бренд' - це не просто текст,
    # а посилання на іншу таблицю 'Brand'.
    # Він автоматично знайде 'Michelin' або СТВОРИТЬ його, якщо не знайде.
    brand = fields.Field(
        column_name='Бренд',
        attribute='brand',
        widget=ForeignKeyWidget(Brand, 'name'))

    # Створюємо "віртуальні" поля, бо 'Типоразмер' не існує в базі
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
        # Вказуємо, які поля моделі ми хочемо заповнити
        fields = ('id', 'name', 'brand', 'width', 'profile', 'diameter', 'seasonality', 'cost_price', 'stock_quantity')
        # Вказуємо, які стовпці читати з CSV
        export_order = ('id', 'Бренд', 'Модель', 'Типоразмер', 'Сезон', 'Цена', 'Кол-во')
        
        # Це "клей" - кажемо, як називаються стовпці у файлі
        import_id_fields = ('id',)
        skip_unchanged = True
        report_skipped = True
        
        # Назви стовпців у вашому CSV (з вашого скріншоту)
        map_field_name = {
            'name': 'Модель',
            'seasonality': 'Сезон',
            'cost_price': 'Цена',
            'stock_quantity': 'Кол-во',
        }

    # "Магія" для обробки стовпців перед збереженням

    def before_import_row(self, row, **kwargs):
        # 1. Обробка 'Типоразмер'
        size_str = row.get('Типоразмер', '')
        match = SIZE_REGEX.search(size_str)
        if match:
            row['width'] = match.group(1)
            row['profile'] = match.group(2)
            row['diameter'] = match.group(3)
        
        # 2. Обробка 'Сезон'
        season_str = row.get('Сезон', '').strip().lower()
        if season_str in self.season_mapping:
            row['Сезон'] = self.season_mapping[season_str] # Замінюємо "зима" на "winter"

        # 3. Обробка 'Кол-во' (Наявність)
        quantity_str = row.get('Кол-во', '0').strip()
        if quantity_str == '>12':
            row['Кол-во'] = 20 # Ставимо "багато"
        elif not quantity_str.isdigit():
            row['Кол-во'] = 0 # Якщо там "немає" або інший текст
        
        # 4. Обробка 'Бренд'
        # (ми робимо це, щоб 'Brand.objects.get_or_create' спрацював)
        brand_name = row.get('Бренд')
        if brand_name:
            Brand.objects.get_or_create(name=brand_name)
            
    # Прив'язуємо наші "віртуальні" поля до реальних
    def dehydrate_width(self, product):
        return product.width
    def dehydrate_profile(self, product):
        return product.profile
    def dehydrate_diameter(self, product):
        return product.diameter
