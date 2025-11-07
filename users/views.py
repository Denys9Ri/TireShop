from django.shortcuts import render
# Це "фейс-контроль" від Django. Не пустить анонімних користувачів.
from django.contrib.auth.decorators import login_required
# Нам потрібна модель 'Order' з магазину, щоб знайти замовлення
from store.models import Order

# --- 1. СТОРІНКА КАБІНЕТУ ---

@login_required # <-- той самий "фейс-контроль"
def profile_view(request):
    # Шукаємо в базі всі замовлення, де поле 'customer'
    # дорівнює поточному залогіненому користувачу (request.user).
    # Сортуємо від найновішого до найстарішого.
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    
    # "Малюємо" сторінку 'profile.html', передаючи їй список замовлень
    return render(request, 'users/profile.html', {'orders': orders})
# Додаємо нові інструменти вгорі файлу
from django.urls import reverse_lazy
from django.views import generic
from .forms import CustomUserCreationForm

# --- 2. СТОРІНКА РЕЄСТРАЦІЇ ---
# Ми використовуємо "generic view" - це готовий клас від Django

class RegisterView(generic.CreateView):
    form_class = CustomUserCreationForm
    # Після успішної реєстрації, перенаправляємо на сторінку ВХОДУ
    success_url = reverse_lazy('login') 
    # HTML-файл, який ми створимо наступним кроком
    template_name = 'registration/register.html'
