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
        price_str = str(product.price) # Тільки текст!

        if product_id not in self.cart:
            self.cart[product_id] = {
                'quantity': 0,
                'price': price_str
            }
        
        # Оновлюємо ціну (текстом)
        self.cart[product_id]['price'] = price_str

        if update_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity
            
        self.save()

    def save(self):
        self.session.modified = True

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __iter__(self):
        """
        Перебираємо товари в кошику.
        """
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        
        # Створюємо тимчасовий словник для продуктів, щоб не смикати базу в циклі
        product_map = {str(p.id): p for p in products}

        for product_id, item in self.cart.items():
            # 🔥 НАЙВАЖЛИВІШИЙ МОМЕНТ:
            # Ми робимо .copy(), щоб не змінювати дані в самій сесії!
            # Якщо ми змінимо item напряму, Django знову спробує зберегти Decimal і впаде.
            current_item = item.copy()
            
            product = product_map.get(product_id)
            if product:
                current_item['product'] = product
                # Тут безпечно перетворюємо в Decimal для обчислень (тільки в копії)
                price_dec = Decimal(str(current_item['price']))
                current_item['price'] = price_dec
                current_item['total_price'] = price_dec * current_item['quantity']
                
                yield current_item

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        total = Decimal('0.00')
        for item in self.cart.values():
            try:
                price = Decimal(str(item['price']))
                total += price * item['quantity']
            except: pass
        return total

    def clear(self):
        del self.session[settings.CART_SESSION_ID]
        self.save()
