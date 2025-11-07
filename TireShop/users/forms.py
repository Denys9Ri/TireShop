from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

# Це стандартна форма реєстрації Django, 
# ми просто кажемо їй, яку модель використовувати
class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        # Ви можете додати 'email' сюди, якщо хочете
        fields = ('username', 'first_name', 'last_name')
