from django.urls import path
from django.contrib.auth import views as auth_views # Додаємо імпорт стандартних view
from . import views

app_name = 'users'

urlpatterns = [
    # Ваші існуючі view
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),

    # 🔥 ДОДАЄМО ВХІД ТА ВИХІД (Цього не вистачало!) 🔥
    # Тепер users:login та users:logout будуть існувати
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='store:catalog'), name='logout'),
]
