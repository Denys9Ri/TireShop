from django.core.management.base import BaseCommand
from store.models import Product
import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import re

# --- СЛОВНИКИ ІНДЕКСІВ (Безкоштовна база знань) ---
SPEED_INDICES = {
    'J': '100', 'K': '110', 'L': '120', 'M': '130', 'N': '140', 'P': '150',
    'Q': '160', 'R': '170', 'S': '180', 'T': '190', 'U': '200', 'H': '210',
    'V': '240', 'W': '270', 'Y': '300', 'ZR': 'понад 240'
}

LOAD_INDICES = {
    '80': '450', '81': '462', '82': '475', '83': '487', '84': '500', '85': '515',
    '86': '530', '87': '545', '88': '560', '89': '580', '90': '600', '91': '615',
    '92': '630', '93': '650', '94': '670', '95': '690', '96': '710', '97': '730',
    '98': '750', '99': '775', '100': '800', '101': '825', '102': '850', '103': '875',
    '104': '900', '105': '925', '106': '950', '107': '975', '108': '1000', '109': '1030',
    '110': '1060', '111': '1090', '112': '1120', '113': '1150', '114': '1180', '115': '1215',
    '116': '1250', '117': '1285', '118': '1320', '119': '1360', '120': '1400'
}

class Command(BaseCommand):
    help = 'Розумний Бот-Парсер для заповнення характеристик шин'

    def scrape_missing_data(self, query_string):
        """
        Бот йде на сайт-донор, шукає шину і витягує 3 параметри.
        """
        tread_type = "Не вказано"
        fuel_economy = "Не вказано"
        noise_level = "Не вказано"
        
        # Маскуємося під звичайний браузер (щоб не заблокували)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'uk,en-US;q=0.9,en;q=0.8'
        }

        try:
            # 1. Робимо пошук по Інфошині
            encoded_query = urllib.parse.quote(query_string)
            search_url = f"https://infoshina.com.ua/uk/search?search={encoded_query}"
            
            response = requests.get(search_url, headers=headers, timeout=7)
            if response.status_code != 200:
                return tread_type, fuel_economy, noise_level

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 2. Шукаємо перше посилання на товар
            product_link = None
            for a_tag in soup.find_all('a', href=True):
                if '/uk/' in a_tag['href'] and ('shina' in a_tag['href'] or 'shini' in a_tag['href']):
                    product_link = a_tag['href']
                    break
                    
            if not product_link:
                return tread_type, fuel_economy, noise_level

            if not product_link.startswith('http'):
                product_link = 'https://infoshina.com.ua' + product_link

            # 3. Заходимо в саму карточку товару конкурента
            prod_response = requests.get(product_link, headers=headers, timeout=7)
            prod_soup = BeautifulSoup(prod_response.text, 'html.parser')

            # 4. Шукаємо ключові слова по всій сторінці (або в таблицях)
            text_blocks = prod_soup.stripped_strings
            
            # Логіка "розумного читання": йдемо по тексту, якщо бачимо назву характеристики, беремо наступне слово
            elements = list(text_blocks)
            for i, text in enumerate(elements):
                text_lower = text.lower()
                
                # Шукаємо тип протектору
                if "протектор" in text_lower and i + 1 < len(elements):
                    val = elements[i+1].strip()
                    if len(val) > 3 and len(val) < 20: 
                        tread_type = val.capitalize()
                
                # Шукаємо економію палива
                elif "палив" in text_lower and i + 1 < len(elements):
                    val = elements[i+1].strip()
                    if len(val) == 1 and val.isalpha(): # Зазвичай це буква A, B, C...
                        fuel_economy = val.upper()
                
                # Шукаємо рівень шуму
                elif "шум" in text_lower and i + 1 < len(elements):
                    val = elements[i+1].strip()
                    if "db" in val.lower() or "дб" in val.lower() or val.isdigit():
                        noise_level = val if "dB" in val else f"{val} dB"

            return tread_type, fuel_economy, noise_level

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Помилка парсингу: {e}"))
            return tread_type, fuel_economy, noise_level

    def handle(self, *args, **kwargs):
        # Беремо товари, у яких ще немає нормального HTML опису
        products = Product.objects.exclude(description__icontains='<ul>')
        total = products.count()
        
        self.stdout.write(self.style.WARNING(f'🚀 Запуск Бота-Парсера. Знайдено товарів без опису: {total}'))

        for i, product in enumerate(products, 1):
            # Формуємо базові змінні з нашої БД
            season_str = product.get_seasonality_display().lower()
            veh_type = product.vehicle_type.lower() if product.vehicle_type else "легкова"
            country = product.country if (product.country and product.country != "-") else "Не вказано"
            year = product.year
            brand_name = product.brand.name if product.brand else ""
            
            # Розшифровуємо індекси через наші словники
            speed_val = product.speed_index or ""
            speed_kmh = SPEED_INDICES.get(speed_val.upper(), "???")
            
            load_val = product.load_index or ""
            load_kg = LOAD_INDICES.get(load_val, "???")

            # Рядок пошуку для бота (наприклад: "Bridgestone Turanza 6 265/50 R20")
            search_query = f"{brand_name} {product.name} {product.width}/{product.profile} R{product.diameter}"
            
            self.stdout.write(f"[{i}/{total}] Шукаю інформацію для: {search_query}...")
            
            # Запускаємо бота парсити відсутні дані
            tread, fuel, noise = self.scrape_missing_data(search_query)

            # Генеруємо твій ідеальний HTML-шаблон
            html_description = f"""<div>
    <strong>Шина {veh_type}, {season_str}</strong><br>
    <ul>
        <li><strong>Країна виробник:</strong> {country} ({year} рік)</li>
        <li><strong>Індекс швидкості:</strong> {speed_val} (до {speed_kmh} км/год)</li>
        <li><strong>Індекс навантаження:</strong> {load_val} (до {load_kg} кг)</li>
        <li><strong>Тип протектору:</strong> {tread}</li>
        <li><strong>Економія палива:</strong> {fuel}</li>
        <li><strong>Рівень шуму:</strong> {noise}</li>
    </ul>
</div>"""

            # Зберігаємо в базу
            product.description = html_description
            product.save(update_fields=['description'])
            
            self.stdout.write(self.style.SUCCESS(f'✅ Готово: {product.brand} {product.name}'))
            
            # Пауза 1.5 секунди, щоб сайт конкурента не забанив твій сервер за DDoS
            time.sleep(1.5) 

        self.stdout.write(self.style.SUCCESS('🔥 Всі описи та характеристики успішно згенеровано!'))
