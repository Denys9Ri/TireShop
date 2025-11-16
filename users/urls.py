from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Старий шлях до кабінету
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),

    # НОВИЙ шлях до реєстрації
    # (views.RegisterView.as_view() - так викликаються Класи-інженери)
    path('register/', views.RegisterView.as_view(), name='register'),
]
