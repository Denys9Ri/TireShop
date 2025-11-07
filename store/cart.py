from decimal import Decimal
from django.conf import settings
from .models import Product

class Cart:
    def __init__(self, request):
        """
        Ініціалізуємо кошик.
        """
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            # Якщо кошика в сесії немає, створюємо порожній
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, update_quantity=False):
        """
        Додати товар в кошик або оновити його кількість.
        """
        product_id = str(product.id)
        
        if product_id not in self.cart:
            # Використовуємо .price, яке вже має вашу націнку 30%
            self.cart[product_id] = {'quantity': 0,
                                     'price': str(product.price)}

        if update_quantity:
            # Пряма зміна кількості (наприклад, у кошику)
            self.cart[product_id]['quantity'] = quantity
        else:
            # Додавання до існуючої кількості (кнопка "В кошик")
            self.cart[product_id]['quantity'] += quantity
        
        self.save()

    def save(self):
        # Позначити сесію як "змінену", щоб Django її зберіг
        self.session.modified = True

    def remove(self, product):
        """
        Видалити товар з кошика.
        """
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __iter__(self):
        """
        Перебір товарів в кошику та отримання їх з БД.
        Це потрібно, щоб в HTML ми могли отримати фото, назву і т.д.
        """
        product_ids = self.cart.keys()
        # Отримуємо самі об'єкти товарів з бази
        products = Product.objects.filter(id__in=product_ids)
        
        cart = self.cart.copy()
        
        for product in products:
            cart[str(product.id)]['product'] = product

        for item in cart.values():
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item

    def __len__(self):
        """
        Підрахунок всіх товарів в кошику (загальна кількість).
        """
        return sum(item['quantity'] for item in self.cart.values())
        
    def get_total_price(self):
        """
        Підрахунок загальної вартості всіх товарів в кошику.
        """
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def clear(self):
        # Видалення кошика з сесії (після оформлення замовлення)
        del self.session[settings.CART_SESSION_ID]
        self.save()
