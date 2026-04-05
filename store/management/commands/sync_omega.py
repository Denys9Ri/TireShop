import requests
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Швидка синхронізація цін та залишків шин через Omega JSON API'

    def handle(self, *args, **options):
        self.stdout.write("🚀 Запуск швидкого оновлення через Omega API...")
        
        # 🔥 СЮДИ ТИ ВСТАВИШ КЛЮЧ, КОЛИ ВІН ПРИЙДЕ 🔥
        API_KEY = "ТВІЙ_МАЙБУТНІЙ_КЛЮЧ"
        
        if API_KEY == "ТВІЙ_МАЙБУТНІЙ_КЛЮЧ":
            self.stderr.write("❌ Стоп! Ви ще не вставили свій API ключ від Омеги.")
            self.stderr.write("Відкрийте файл store/management/commands/sync_omega.py і замініть 'ТВІЙ_МАЙБУТНІЙ_КЛЮЧ' на реальний ключ.")
            return

        url = "https://public.omega.page/public/api/v1.0/searchcatalog/getTires"
        headers = {"Content-Type": "application/json"}
        payload = {
            "Key": API_KEY,
        }

        self.stdout.write("📥 Запит до API (getTires)...")
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            
            if not response.ok:
                self.stderr.write(f"❌ Помилка HTTP {response.status_code}: {response.text}")
                return

            # Спробуємо розпарсити JSON
            data = response.json()
            
            # Шукаємо список товарів у відповіді
            tires_list = None
            if isinstance(data, dict):
                if "Data" in data:
                    tires_list = data["Data"]
                elif "Result" in data:
                    tires_list = data["Result"]
            elif isinstance(data, list):
                tires_list = data

            if tires_list is None:
                self.stderr.write(f"❌ Невідома структура відповіді: {str(data)[:200]}...")
                return

            self.stdout.write(f"✅ Отримано товарів: {len(tires_list)}")
            
            if len(tires_list) == 0:
                self.stdout.write("⚠️ API повернуло пустий список. Перевірте ключ або налаштування в Омезі.")
                return

            # Покажемо структуру першого товару для розвідки
            first_tire = tires_list[0]
            self.stdout.write("\n🔍 СТРУКТУРА ПЕРШОГО ТОВАРУ (JSON):")
            self.stdout.write(f"ID (Number/ProductId): {first_tire.get('Number') or first_tire.get('ProductId')}")
            self.stdout.write(f"Бренд: {first_tire.get('BrandDescription')}")
            self.stdout.write(f"Назва: {first_tire.get('Description')}")
            self.stdout.write(f"Ціна (Price / CustomerPrice): {first_tire.get('Price')} / {first_tire.get('CustomerPrice')}")
            self.stdout.write(f"Залишок (EffectiveQuantity): {first_tire.get('EffectiveQuantity')}")
            self.stdout.write("-" * 40 + "\n")

            self.stdout.write("⚠️ РОБОТ ЗУПИНЕНИЙ ДЛЯ ПЕРЕВІРКИ. Скинь ці дані розробнику (мені).")
            
        except requests.exceptions.RequestException as e:
            self.stderr.write(f"❌ Помилка з'єднання з сервером Омеги: {e}")
        except Exception as e:
            self.stderr.write(f"❌ Системна помилка під час обробки JSON: {e}")
