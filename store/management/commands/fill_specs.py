from django.core.management.base import BaseCommand
from store.models import Product
import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import re

# --- СЛОВНИКИ ІНДЕКСІВ ---
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
    '116': '1250', '117': '1285', '118': '1320', '119': '1360', '120': '1400',
    '121': '1450', '122': '1500', '123': '1550'
}

class Command(BaseCommand):
    help = 'Бот-Парсер V2.0 для заповнення характеристик шин'

    def scrape_missing_data(self, brand, model, size):
        tread_type = "Не вказано"
        fuel_economy = "Не вказано"
        noise_level = "Не вказано"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'uk,en-US;q=0.9,en;q=0.8'
        }

        try:
            # Спробуємо парсити Shiny-Diski
            query = f"{brand} {model} {size}"
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://shiny-diski.com.ua/uk/search?query={encoded_query}"
            
            response = requests.get(search_url, headers=headers, timeout=10)
            if response.status_code != 200:
                return tread_type, fuel_economy, noise_level

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Шукаємо лінк на товар
            product_link = None
            for a_tag in soup.find_all('a', href=True):
                if '/uk/' in a_tag['href'] and len(a_tag['href']) > 20:
                    product_link = a_tag['href']
                    break
                    
            if not product_link:
                return tread_type, fuel_economy, noise_level

            if not product_link.startswith('http'):
                product_link = 'https://shiny-diski.com.ua' + product_link

            prod_response = requests.get(product_link, headers=headers, timeout=10)
            prod_soup = BeautifulSoup(prod_response.text, 'html.parser')

            # Шукаємо в таблицях характеристик
            for tr in prod_soup.find_all('tr'):
                text_lower = tr.get_text().lower()
                tds = tr.find_all('td')
                if len(tds) >= 2:
                    val = tds[1].get_text(strip=True)
                    
                    if "протектор" in text_lower:
                        if len(val) > 2: tread_type = val.capitalize()
                    elif "палив" in text_lower:
                        if len(val) == 1: fuel_economy = val.upper()
                    elif "шум" in text_lower:
                        if val: noise_level = val if "dB" in val else f"{val} dB"

            return tread_type, fuel_economy, noise_level

        except Exception as e:
            return tread_type, fuel_economy, noise_level

    def handle(self, *args, **kwargs):
        products = Product.objects.exclude(description__icontains='<ul>')
        total = products.count()
        
        self.stdout.write(self.style.WARNING(f'🚀 Запуск Бота V2. Знайдено товарів без опису: {total}'))

        for i, product in enumerate(products, 1):
            # 1. ГРАМАТИКА (Виправляємо стать шини)
            veh_type = product.vehicle_type.lower() if product.vehicle_type else "легковий"
            if "легков" in veh_type: veh_type = "легкова"
            elif "позашлях" in veh_type or "suv" in veh_type: veh_type = "для позашляховиків"
            elif "вантаж" in veh_type or "коммерц" in veh_type: veh_type = "легковантажна"
            
            season_str = product.get_seasonality_display().lower()
            country = product.country if (product.country and product.country != "-") else "Не вказано"
            year = product.year
            
            # 2. РОЗУМНИЙ ПОШУК ІНДЕКСІВ (Навіть якщо в базі пусто, шукаємо в назві!)
            speed_val = product.speed_index or ""
            load_val = product.load_index or ""
            
            if not speed_val or not load_val:
                # Шукаємо комбінацію типу "111W" або "98 Y" в назві товару
                match = re.search(r'\b(\d{2,3})([A-Z]{1,2})\b', product.name.upper())
                if match:
                    if not load_val: load_val = match.group(1)
                    if not speed_val: speed_val = match.group(2)

            speed_kmh = SPEED_INDICES.get(speed_val.upper(), "???") if speed_val else "???"
            load_kg = LOAD_INDICES.get(load_val, "???") if load_val else "???"

            # 3. ПАРСИНГ З ІНТЕРНЕТУ
            brand_name = product.brand.name if product.brand else ""
            size_str = f"{product.width}/{product.profile} R{product.diameter}"
            
            self.stdout.write(f"[{i}/{total}] Обробка: {brand_name} {product.name}...")
            
            tread, fuel, noise = self.scrape_missing_data(brand_name, product.name, size_str)

            # 4. ФОРМУВАННЯ HTML
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

            product.description = html_description
            product.save(update_fields=['description'])
            
            self.stdout.write(self.style.SUCCESS(f'✅ Успіх!'))
            time.sleep(1)

        self.stdout.write(self.style.SUCCESS('🔥 Завершено!'))
