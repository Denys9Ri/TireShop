from django.core.management.base import BaseCommand
from store.models import Product

class Command(BaseCommand):
    help = 'Очищення проблемних товарів перед пошуком у Google'

    def handle(self, *args, **options):
        # Визначаємо бренди, які треба переробити через Google
        # Можеш додати сюди інші бренди через кому
        brands_to_fix = ['Ovation', 'Leao'] 
        
        products = Product.objects.filter(
            name__regex=r'(' + '|'.join(brands_to_fix) + r')'
        )

        self.stdout.write(self.style.WARNING(f"🧹 Очищення {products.count()} товарів бренду {brands_to_fix}..."))

        # Очищаємо фото та опис, щоб find_images побачив їх як "пусті"
        products.update(photo='', description='')
        
        self.stdout.write(self.style.SUCCESS("✅ Готово. Тепер ці товари порожні і готові для Serper."))
