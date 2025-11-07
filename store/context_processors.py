from .cart import Cart

def cart(request):
    # Ця функція просто бере поточний запит (request),
    # створює об'єкт кошика (з сесії)
    # і повертає його у словнику під ключем 'cart'.
    return {'cart': Cart(request)}
