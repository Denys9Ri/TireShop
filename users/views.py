from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import generic

from store.models import Order
from .forms import CustomUserCreationForm, ProfileUpdateForm, UserUpdateForm
from .models import UserProfile

# --- 1. СТОРІНКА КАБІНЕТУ (з "чарівним" кодом) ---

@login_required 
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    return render(request, 'users/profile.html', {'orders': orders, 'profile': profile})


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


# --- 2. СТОРІНКА РЕЄСТРАЦІЇ (без змін) ---
class RegisterView(generic.CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login') 
    template_name = 'registration/register.html'
