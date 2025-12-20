from decimal import Decimal
from django.conf import settings
from .models import Product

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, update_quantity=False):
        product_id = str(product.id)
        
        # Одразу перетворюємо в str, щоб уникнути помилок
        price_str = str(product.price)

        if product_id not in self.cart:
            self.cart[product_id] = {
                'quantity': 0,
                'price': price_str
            }
        
        # Оновлюємо ціну
        self.cart[product_id]['price'] = price_str

        if update_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity
            
        self.save()

    def save(self):
        # 🔥 БРОНЕБІЙНИЙ ЗАХИСТ ВІД DECIMAL 🔥
        # Перед тим як сказати джанго "збережи", ми проходимось по всьому кошику
        # і гарантуємо, що ціна - це рядок.
        for item in self.cart.values():
            if 'price' in item:
                item['price'] = str(item['price'])
        
        self.session.modified = True

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        cart = self.cart.copy()

        for product in products:
            cart[str(product.id)]['product'] = product

        for item in cart.values():
            # Тут перетворюємо назад у числа для математики на сторінці
            # Використовуємо try/except, щоб не впало, якщо там сміття
            try:
                price_dec = Decimal(str(item['price']))
            except:
                price_dec = Decimal('0')
                
            item['price'] = price_dec
            item['total_price'] = price_dec * item['quantity']
            yield item

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        total = Decimal('0')
        for item in self.cart.values():
            try:
                price = Decimal(str(item['price']))
                qty = item['quantity']
                total += price * qty
            except:
                pass
        return total

    def clear(self):
        del self.session[settings.CART_SESSION_ID]
        self.save()
