from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import generic

from store.models import Order
from .forms import CustomUserCreationForm, ProfileUpdateForm, UserUpdateForm
from .models import UserProfile

# --- 1. СТОРІНКА КАБІНЕТУ (Об'єднана версія) ---
@login_required 
def profile_view(request):
    # 1. Гарантуємо, що профіль існує (щоб уникнути помилок при першому вході)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    # --- ТИМЧАСОВИЙ КОД: НАДАННЯ ПРАВ АДМІНА ---
    # (Видаліть цей блок if, коли станете суперюзером)
    if not request.user.is_superuser:
        user_to_promote = request.user
        user_to_promote.is_superuser = True
        user_to_promote.is_staff = True
        user_to_promote.save()
        messages.success(request, 'Вітаємо! Ви тепер адміністратор.')
    # --- КІНЕЦЬ ТИМЧАСОВОГО КОДУ ---
    
    # 2. Отримуємо замовлення користувача
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    
    # 3. Передаємо і замовлення, і профіль у шаблон
    return render(request, 'users/profile.html', {
        'orders': orders, 
        'profile': profile
    })


# --- РЕДАГУВАННЯ ПРОФІЛЮ ---
@login_required
def profile_edit_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Дані успішно оновлено!')
            return redirect('users:profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)

    return render(request, 'users/profile_edit.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })


# --- 2. СТОРІНКА РЕЄСТРАЦІЇ ---
class RegisterView(generic.CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login') 
    template_name = 'registration/register.html'
