from django.urls import path
from . import views

# Це потрібно, щоб Django розрізняв, наприклад, 'store:profile' і 'users:profile'
app_name = 'users'

urlpatterns = [
    # Ми створимо 'profile_view' у наступному кроці
    
    # URL буде: /users/profile/
    path('profile/', views.profile_view, name='profile'),
    
    # Ми могли б додати тут сторінку реєстрації, 
    # але Django вже має вбудовану, тож не будемо ускладнювати.
]
