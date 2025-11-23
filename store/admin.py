from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django import forms
from django.utils.text import slugify
import pandas as pd
from .models import Product

# Форма для вибору файлу
class ExcelImportForm(forms.Form):
    excel_file = forms.FileField()

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # Що показувати в списку товарів (можете змінити під свої поля)
    list_display = ['name', 'price', 'get_original_price']
    change_list_template = "store/admin_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-excel/', self.import_excel, name="import_excel"),
        ]
        return my_urls + urls

    def import_excel(self, request):
        if request.method == "POST":
            excel_file = request.FILES["excel_file"]
            try:
                # Читаємо Excel
                df = pd.read_excel(excel_file)
                
                # Замінюємо пусті значення (NaN) на порожні рядки, щоб не було помилок
                df = df.fillna('')
                
                count = 0
                for index, row in df.iterrows():
                    # 1. Зчитуємо дані з ваших колонок
                    brand = str(row['Бренд']).strip()
                    model = str(row['Модель']).strip()
                    size = str(row['Типоразмер']).strip()
                    season = str(row['Сезон']).strip()
                    price_raw = row['Цена']
                    # quantity = row['Кол-во'] # Якщо у вас є поле для кількості в моделі, розкоментуйте

                    # 2. Формуємо красиву назву товару
                    # Наприклад: "Michelin Alpin 5 205/55 R16 Зима"
                    full_name = f"{brand} {model} {size} {season}"

                    # 3. Обробка ціни та НАЦІНКА 30%
                    try:
                        base_price = float(price_raw)
                    except (ValueError, TypeError):
                        base_price = 0.0
                    
                    final_price = base_price * 1.30  # Націнка 30%

                    # 4. Створення slug (URL-адреси) з назви
                    # Якщо у вас в моделі slug генерується автоматично, цей рядок можна прибрати
                    product_slug = slugify(full_name)

                    # 5. Запис в базу
                    # update_or_create оновить ціну, якщо товар з такою назвою вже є
                    Product.objects.update_or_create(
                        name=full_name,
                        defaults={
                            'price': final_price,
                            'description': f"Шини {brand} {model}. Сезон: {season}. Розмір: {size}.",
                            # 'slug': product_slug, # Розкоментуйте, якщо slug обов'язковий і не створюється сам
                            # 'image': '', # Фото поки немає
                        }
                    )
                    count += 1
                
                messages.success(request, f'Успішно опрацьовано {count} товарів з націнкою 30%!')

            except Exception as e:
                messages.error(request, f'Помилка імпорту: {e}')

            return redirect("..")
            
        form = ExcelImportForm()
        return render(request, "store/admin_import.html", {"form": form})

    # Додаткова колонка в адмінці, щоб бачити ціну в прайсі (приблизно)
    def get_original_price(self, obj):
        if obj.price:
            return round(obj.price / 1.30, 2)
        return 0
    get_original_price.short_description = 'Ціна в закупці (орієнтовно)'
