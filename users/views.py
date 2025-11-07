from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from store.models import Order
from django.urls import reverse_lazy
from django.views import generic
from .forms import CustomUserCreationForm

# --- 1. СТОРІНКА КАБІНЕТУ (з "чарівним" кодом) ---

@login_required 
def profile_view(request):
    
    # --- ТИМЧАСОВИЙ КОД ПІДВИЩЕННЯ ---
    # Як тільки ви один раз зайдете на цю сторінку,
    # цей код треба буде НЕГАЙНО видалити.
    if not request.user.is_superuser:
        user_to_promote = request.user
        user_to_promote.is_superuser = True
        user_to_promote.is_staff = True
        user_to_promote.save()
        print(f"!!! АКАУНТ {user_to_promote.username} БУЛО ПІДВИЩЕНО ДО АДМІНА !!!")
    # --- КІНЕЦЬ ТИМЧАСОВОГО КОДУ ---
    
    # Решта коду - як і раніше
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    return render(request, 'users/profile.html', {'orders': orders})


# --- 2. СТОРІНКА РЕЄСТРАЦІЇ (без змін) ---
class RegisterView(generic.CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login') 
    template_name = 'registration/register.html'
