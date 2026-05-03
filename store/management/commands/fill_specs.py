from django.core.management.base import BaseCommand
from store.models import Product
from bs4 import BeautifulSoup
import urllib.parse
import time
import re
import cloudscraper

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
    help = 'Бот-Парсер V3.0 (Cloudscraper) для обходу захисту'

    def scrape_missing_data(self, brand, model, size):
        tread_type = "Не вказано"
        fuel_economy = "Не вказано"
        noise_level = "Не вказано"
        
        # Створюємо scraper, який вміє обходити Cloudflare
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )

        try:
            # Формуємо запит (шукаємо спочатку на shiny-diski)
            query = f"{brand} {model} {size}"
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://shiny-diski.com.ua/uk/search?query={encoded_query}"
            
            response = scraper.get(search_url, timeout=15)
            
            # Якщо shiny-diski не відповів, пробуємо infoshina
            if response.status_code != 200:
                search_url = f"https://infoshina.com.ua/uk/search?search={encoded_query}"
                response = scraper.get(search_url, timeout=15)
                if response.status_code != 200:
                    return tread_type, fuel_economy, noise_level

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Знаходимо перше посилання на товар в результатах пошуку
            product_link = None
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if '/uk/' in href and ('shina' in href or 'shini' in href or 'tires' in href or brand.lower() in href.lower()):
                    if len(href) > 20:
                        product_link = href
                        break

            if not product_link:
                return tread_type, fuel_economy, noise_level

            # Робимо повне посилання
            if product_link.startswith('/'):
                if 'infoshina' in search_url:
                    product_link = 'https://infoshina.com.ua' + product_link
                else:
                    product_link = 'https://shiny-diski.com.ua' + product_link

            # Заходимо в саму карточку
            prod_response = scraper.get(product_link, timeout=15)
            prod_soup = BeautifulSoup(prod_response.text, 'html.parser')

            # Шукаємо у всіх можливих контейнерах характеристик (таблиці, списки, діви)
            for element in prod_soup.find_all(['tr', 'li', 'div']):
                text_lower = element.get_text(separator=' ').lower()
                
                # 1. Протектор
                if "протектор" in text_lower or "малюнок" in text_lower:
                    tds = element.find_all(['td', 'span', 'b', 'strong'])
                    if len(tds) >= 2:
                        val = tds[-1].get_text(strip=True)
                        if len(val) > 3 and "протект" not in val.lower():
                            tread_type = val.capitalize()
                    else:
                        parts = element.get_text(separator=':').split(':')
                        if len(parts) >= 2:
                            val = parts[-1].strip()
                            if len(val) > 3 and len(val) < 20: tread_type = val.capitalize()

                # 2. Паливо (шукаємо одну літеру A-G)
                if "палив" in text_lower or "опір коченню" in text_lower:
                    tds = element.find_all(['td', 'span', 'b', 'strong'])
                    if len(tds) >= 2:
                        val = tds[-1].get_text(strip=True).upper()
                        if len(val) == 1 and val in 'ABCDEFG': fuel_economy = val
                    else:
                        parts = element.get_text(separator=':').split(':')
                        if len(parts) >= 2:
                            val = parts[-1].strip().upper()
                            if len(val) == 1 and val in 'ABCDEFG': fuel_economy = val

                # 3. Шум (шукаємо цифри + dB/дБ)
                if "шум" in text_lower:
                    val = element.get_text(separator=' ')
                    match = re.search(r'(\d{2})\s*(db|дб)', val, re.IGNORECASE)
                    if match:
                        noise_level = f"{match.group(1)} dB"
                    else:
                        match2 = re.search(r'(\d{2})', val)
                        if match2 and 60 <= int(match2.group(1)) <= 80:
                            noise_level = f"{match2.group(1)} dB"

            return tread_type, fuel_economy, noise_level

        except Exception as e:
            # Тихий фейл, щоб не зупиняти весь процес
            return tread_type, fuel_economy, noise_level

    def handle(self, *args, **kwargs):
        products = Product.objects.exclude(description__icontains='<ul>')
        total = products.count()
        
        self.stdout.write(self.style.WARNING(f'🚀 Запуск Бота V3 (Cloudscraper). Залишилось обробити: {total}'))

        for i, product in enumerate(products, 1):
            # ГРАМАТИКА
            veh_type = product.vehicle_type.lower() if product.vehicle_type else "легковий"
            if "легков" in veh_type: veh_type = "легкова"
            elif "позашлях" in veh_type or "suv" in veh_type: veh_type = "для позашляховиків"
            elif "вантаж" in veh_type or "коммерц" in veh_type: veh_type = "легковантажна"
            
            season_str = product.get_seasonality_display().lower()
            country = product.country if (product.country and product.country != "-") else "Не вказано"
            year = product.year
            
            # ІНДЕКСИ (Беремо з БД або витягуємо з назви)
            speed_val = product.speed_index or ""
            load_val = product.load_index or ""
            
            if not speed_val or not load_val:
                match = re.search(r'\b(\d{2,3})([A-Z]{1,2})\b', product.name.upper())
                if match:
                    if not load_val: load_val = match.group(1)
                    if not speed_val: speed_val = match.group(2)

            speed_kmh = SPEED_INDICES.get(speed_val.upper(), "???") if speed_val else "???"
            load_kg = LOAD_INDICES.get(load_val, "???") if load_val else "???"

            # ПАРСИНГ З ІНТЕРНЕТУ
            brand_name = product.brand.name if product.brand else ""
            size_str = f"{product.width}/{product.profile} R{product.diameter}"
            
            self.stdout.write(f"[{i}/{total}] Парсинг: {brand_name} {product.name}...")
            
            tread, fuel, noise = self.scrape_missing_data(brand_name, product.name, size_str)

            # ФОРМУВАННЯ HTML
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
            
            self.stdout.write(self.style.SUCCESS(f'✅ Готово: Протектор: {tread} | Паливо: {fuel} | Шум: {noise}'))
            time.sleep(2) # Пауза 2 секунди, щоб нас не забанили

        self.stdout.write(self.style.SUCCESS('🔥 Всі дані успішно спарсено та згенеровано!'))
