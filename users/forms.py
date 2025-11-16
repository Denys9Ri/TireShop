from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile

# Це стандартна форма реєстрації Django, 
# ми просто кажемо їй, яку модель використовувати
class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        # Ви можете додати 'email' сюди, якщо хочете
        fields = ('username', 'first_name', 'last_name')


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
        labels = {
            'username': 'Логін',
            'first_name': "Ім'я",
            'last_name': 'Прізвище',
            'email': 'Пошта',
        }


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('phone_primary', 'phone_secondary', 'city', 'nova_poshta_branch')
        labels = {
            'phone_primary': 'Номер телефону',
            'phone_secondary': 'Додатковий телефон',
            'city': 'Місто / Село',
            'nova_poshta_branch': 'Відділення або поштомат НП',
        }
