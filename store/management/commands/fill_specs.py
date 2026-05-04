from django.core.management.base import BaseCommand
from store.models import Product
from django.db.models import Q
from django.conf import settings
import time
import re
import json
import logging
from openai import OpenAI

# 🔥 Глушимо системний спам від OpenAI (HTTP 200 OK) 🔥
logging.getLogger("httpx").setLevel(logging.WARNING)

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# --- БАЗИ ЗНАНЬ ---
SPEED_INDICES = {
    'J': '100', 'K': '110', 'L': '120', 'M': '130', 'N': '140', 'P': '150',
    'Q': '160', 'R': '170', 'S': '180', 'T': '190', 'U': '200', 'H': '210',
    'V': '240', 'W': '270', 'Y': '300', 'ZR': 'понад 240'
}

LOAD_INDICES = {
    '65': '290', '66': '300', '67': '307', '68': '315', '69': '325',
    '70': '335', '71': '345', '72': '355', '73': '365', '74': '375',
    '75': '387', '76': '400', '77': '412', '78': '425', '79': '437',
    '80': '450', '81': '462', '82': '475', '83': '487', '84': '500', '85': '515',
    '86': '530', '87': '545', '88': '560', '89': '580', '90': '600', '91': '615',
    '92': '630', '93': '650', '94': '670', '95': '690', '96': '710', '97': '730',
    '98': '750', '99': '775', '100': '800', '101': '825', '102': '850', '103': '875',
    '104': '900', '105': '925', '106': '950', '107': '975', '108': '1000', '109': '1030',
    '110': '1060', '111': '1090', '112': '1120', '113': '1150', '114': '1180', '115': '1215',
    '116': '1250', '117': '1285', '118': '1320', '119': '1360', '120': '1400',
    '121': '1450', '122': '1500', '123': '1550', '124': '1600', '125': '1650'
}

BRAND_COUNTRIES = {
    'leao': 'Сербія', 'hankook': 'Південна Корея', 'nexen': 'Південна Корея',
    'bridgestone': 'Японія', 'michelin': 'Франція', 'goodyear': 'США',
    'continental': 'Німеччина', 'pirelli': 'Італія', 'yokohama': 'Японія',
    'toyo': 'Японія', 'kumho': 'Південна Корея', 'roadstone': 'Південна Корея',
    'nokian': 'Фінляндія', 'nokian tyres': 'Фінляндія', 'kapsen': 'Китай',
    'aplus': 'Китай', 'laufenn': 'Південна Корея', 'laufen': 'Південна Корея',
    'ovation': 'Китай', 'росава': 'Україна', 'rosava': 'Україна',
    'premiorri': 'Україна', 'sunny': 'Китай', 'ecovision': 'Китай',
    'habilead': 'Китай', 'triangle': 'Китай', 'sailun': 'Китай',
    'windforce': 'Китай', 'goform': 'Китай', 'lanvigator': 'Китай',
    'mirage': 'Китай', 'hifly': 'Китай', 'goodride': 'Китай',
    'sunfull': 'Китай', 'fronway': 'Китай', 'barum': 'Чехія',
    'sava': 'Словенія', 'matador': 'Словаччина', 'tigar': 'Сербія',
    'orium': 'Сербія', 'taurus': 'Сербія', 'strial': 'Сербія',
    'kormoran': 'Сербія', 'riken': 'Сербія', 'debica': 'Польща',
    'fulda': 'Німеччина', 'falken': 'Японія', 'dunlop': 'Велика Британія',
    'maxxis': 'Тайвань', 'nankang': 'Тайвань', 'lassa': 'Туреччина',
    'petlas': 'Туреччина', 'gislaved': 'Швеція', 'kleber': 'Франція',
    'bfgoodrich': 'США', 'uniroyal': 'США', 'apollo': 'Індія',
    'bkt': 'Індія', 'viatti': 'Росія', 'cachland': 'Китай',
    'voyager': 'Китай', 'compasal': 'Китай', 'kingstar': 'Китай',
    'ozka': 'Туреччина', 'wanli': 'Китай', 'crosswind': 'Китай',
    'linglong': 'Китай', 'firestone': 'США'
}

class Command(BaseCommand):
    help = 'ШІ Бот-Експерт V8.1: Перезаписуємо старі короткі описи'

    def get_ai_specs(self, brand, model, season, veh_type):
        prompt = f"""
        Ти — професійний маркетолог магазину шин 'R16'. 
        Створи опис та характеристики для шини {brand} {model} ({season}, {veh_type}).

        1. Напиши 2-3 речення продаючого тексту. Наголос на безпеку та вигоду покупки в R16.
        2. Вкажи 3 характеристики. Використовуй дані лінійки {brand} {model}. 
        ЗАБОРОНЕНО писати "Не вказано".
        3. Визнач країну походження бренду {brand}.

        Поверни ТІЛЬКИ JSON:
        {{"marketing_text": "текст",
         "tread": "Асиметричний, Симетричний або Направлений",
         "fuel": "одна англійська літера A-G",
         "noise": "рівень шуму (наприклад: 71 dB)",
         "country": "Назва країни"}}
        """
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3 
            )
            data = json.loads(response.choices[0].message.content)
            return (
                data.get("marketing_text", ""),
                data.get("tread", "Асиметричний"), 
                data.get("fuel", "C"), 
                data.get("noise", "71 dB"),
                data.get("country", "Не вказано")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Помилка OpenAI: {e}'))
            return "", "Асиметричний", "C", "71 dB", "Не вказано"

    def handle(self, *args, **kwargs):
        # 🔥 ГОЛОВНИЙ ФІКС: Беремо ВСІ товари, де в описі НЕМАЄ класу 'specs-list-ai' 🔥
        # Це означає, що він візьме і пусті, і зі старим текстом, і перезапише їх.
        products = Product.objects.filter(
            ~Q(description__icontains='specs-list-ai') | Q(description__isnull=True)
        ).order_by('-stock_quantity')
        
        total = products.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('🎉 Всі товари ідеально заповнені! (Нуль товарів у черзі)'))
            return

        self.stdout.write(self.style.WARNING(f'🚀 Запуск Бота V8.1. Товарів до обробки: {total}'))

        for i, product in enumerate(products, 1):
            veh_type = product.vehicle_type.lower() if product.vehicle_type else "легковий"
            if "легков" in veh_type: veh_type = "легкова"
            elif "позашлях" in veh_type or "suv" in veh_type: veh_type = "для позашляховиків"
            
            season_str = product.get_seasonality_display().lower()
            if "всесезон" in season_str: season_str = "всесезонна"
            elif "зимов" in season_str: season_str = "зимова"
            elif "літн" in season_str: season_str = "літня"

            speed_val = product.speed_index or ""
            load_val = product.load_index or ""
            if not speed_val or not load_val:
                match = re.search(r'\b(\d{2,3})([A-Z]{1,2})\b', product.name.upper())
                if match:
                    if not load_val: load_val = match.group(1)
                    if not speed_val: speed_val = match.group(2)

            speed_kmh = SPEED_INDICES.get(speed_val.upper(), "???")
            load_kg = LOAD_INDICES.get(load_val, "???")

            brand_name = product.brand.name if product.brand else ""
            marketing_text, tread, fuel, noise, ai_country = self.get_ai_specs(brand_name, product.name, season_str, veh_type)

            country = None
            clean_brand_name = brand_name.lower().strip()

            match_country = re.search(r'(?:вир-во|в-ва)\s+([А-Яа-яІіЇїЄє]+)', product.name, re.IGNORECASE)
            if match_country: country = match_country.group(1).title()

            if not country and clean_brand_name in BRAND_COUNTRIES:
                country = BRAND_COUNTRIES[clean_brand_name]

            if not country and product.country and product.country.strip().lower() not in ["", "-", "не вказано", "none"]:
                country = product.country.strip()

            if not country and product.brand and product.brand.country and product.brand.country.strip().lower() not in ["", "-", "не вказано", "none"]:
                country = product.brand.country.strip()

            if not country:
                country = ai_country if ai_country.lower() not in ["", "-", "не вказано", "none"] else "Не вказано"

            html_description = f"""<div class="product-description-block">
    <p class="mb-3">{marketing_text}</p>
    <p class="mb-2"><strong>Основні характеристики шини {brand_name} {product.name}:</strong></p>
    <ul class="specs-list-ai">
        <li><strong>Сезон та тип:</strong> {veh_type.capitalize()}, {season_str}</li>
        <li><strong>Країна виробник:</strong> {country}</li>
        <li><strong>Індекс швидкості:</strong> {speed_val} (до {speed_kmh} км/год)</li>
        <li><strong>Індекс навантаження:</strong> {load_val} (до {load_kg} кг)</li>
        <li><strong>Тип протектору:</strong> {tread}</li>
        <li><strong>Економія палива:</strong> {fuel}</li>
        <li><strong>Рівень шуму:</strong> {noise}</li>
    </ul>
</div>"""

            product.description = html_description
            
            try:
                product.save(update_fields=['description'])
                self.stdout.write(self.style.SUCCESS(f'[{i}/{total}] ✅ Оновлено: {brand_name} {product.name}'))
            except Exception as db_err:
                self.stdout.write(self.style.ERROR(f'[{i}/{total}] ❌ ПОМИЛКА ЗБЕРЕЖЕННЯ В БАЗУ (ID {product.id}): {db_err}'))

            time.sleep(0.3)

        self.stdout.write(self.style.SUCCESS('🔥 Всі товари ідеально оновлено!'))
