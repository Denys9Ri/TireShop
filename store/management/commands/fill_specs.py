from django.core.management.base import BaseCommand
from store.models import Product
from django.conf import settings
import time
import re
import json
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)

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
    help = 'ШІ Бот-Експерт для заповнення описів та характеристик шин через OpenAI'

    def get_ai_specs(self, brand, model, season, veh_type):
        prompt = f"""
        Ти — найкращий експерт з автомобільних шин та головний маркетолог магазину 'R16'. 
        Твоє завдання: створити рекламний опис та технічні характеристики для шини {brand} {model}.
        Сезон: {season}. Тип авто: {veh_type}.

        1. Напиши 2-3 речення продаючого тексту про головні переваги цієї моделі (керованість, гальмування, зносостійкість). Нативно згадай магазин R16.
        2. Вкажи 3 характеристики. Використовуй офіційні дані про лінійку {brand} {model}. ЗАБОРОНЕНО писати "Не вказано". Завжди надавай найбільш точне або середнє значення для цієї моделі на ринку.

        Поверни результат ТІЛЬКИ у форматі JSON:
        {{"marketing_text": "твій продаючий текст",
         "tread": "Асиметричний, Симетричний або Направлений",
         "fuel": "одна англійська літера від A до G",
         "noise": "рівень шуму (наприклад: 71 dB)"}}
        """
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini", # Використовуємо новішу і найрозумнішу модель
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3 
            )
            
            data = json.loads(response.choices[0].message.content)
            return (
                data.get("marketing_text", f"Надійні шини {brand} {model} для вашого автомобіля."),
                data.get("tread", "Асиметричний"), 
                data.get("fuel", "C"), 
                data.get("noise", "71 dB")
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Помилка ШІ: {e}"))
            return "", "Асиметричний", "C", "71 dB"

    def handle(self, *args, **kwargs):
        # Шукаємо товари, у яких в описі ще немає HTML-списку <ul>
        products = Product.objects.exclude(description__icontains='<ul>')
        total = products.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('🎉 Всі товари вже мають ідеальний опис!'))
            return

        self.stdout.write(self.style.WARNING(f'🚀 Запуск Ultimate ШІ Бота (GPT-4o-mini). Очікують: {total} товарів'))

        for i, product in enumerate(products, 1):
            veh_type = product.vehicle_type.lower() if product.vehicle_type else "легковий"
            if "легков" in veh_type: veh_type = "легкова"
            elif "позашлях" in veh_type or "suv" in veh_type: veh_type = "для позашляховиків"
            elif "вантаж" in veh_type or "коммерц" in veh_type: veh_type = "легковантажна"
            
            season_str = product.get_seasonality_display().lower()
            country = product.country if (product.country and product.country != "-") else "Не вказано"
            year = product.year
            
            speed_val = product.speed_index or ""
            load_val = product.load_index or ""
            
            if not speed_val or not load_val:
                match = re.search(r'\b(\d{2,3})([A-Z]{1,2})\b', product.name.upper())
                if match:
                    if not load_val: load_val = match.group(1)
                    if not speed_val: speed_val = match.group(2)

            speed_kmh = SPEED_INDICES.get(speed_val.upper(), "???") if speed_val else "???"
            load_kg = LOAD_INDICES.get(load_val, "???") if load_val else "???"

            brand_name = product.brand.name if product.brand else ""
            self.stdout.write(f"[{i}/{total}] ШІ пише текст для: {brand_name} {product.name}...")
            
            marketing_text, tread, fuel, noise = self.get_ai_specs(brand_name, product.name, season_str, veh_type)

            html_description = f"""<div class="product-description-block">
    <p class="mb-3">{marketing_text}</p>
    <p class="mb-2"><strong>Основні характеристики шини {brand_name} {product.name}:</strong></p>
    <ul class="specs-list-ai">
        <li><strong>Сезон та тип:</strong> {veh_type.capitalize()}, {season_str}</li>
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
            
            time.sleep(0.5)

        self.stdout.write(self.style.SUCCESS('🔥 Всі товари заповнені текстами та характеристиками!'))
