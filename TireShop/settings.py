import os
import dj_database_url
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# --- Ключові налаштування безпеки ---

# Render автоматично підставить свій ключ
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-a_dummy_key_for_now_!@#$')

# Render автоматично ставить це в 'False'
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# Render сам додає сюди адресу сайту
ALLOWED_HOSTS = ['*'] # Починаємо з '*'
if not DEBUG and os.environ.get('RENDER_EXTERNAL_HOSTNAME'):
    ALLOWED_HOSTS = [os.environ.get('RENDER_EXTERNAL_HOSTNAME')]


# --- Додатки (Apps) ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Наші додатки
    'store.apps.StoreConfig', 
    'users.apps.UsersConfig', 
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    
    # --- ОСЬ ВАШ ПОМІЧНИК CSS ---
    # Він має бути другим у списку, одразу після SecurityMiddleware
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    
    'django.contrib.sessions.middleware.SessionMiddleware', 
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'TireShop.urls' 


# --- Шаблони (HTML) ---
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        
        # --- ОСЬ ВАШ LOGIN.HTML ---
        # Це каже Django шукати 'login.html' у папці 'TireShop/templates/'
        'DIRS': [BASE_DIR / 'templates'], 
        
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'store.context_processors.cart',
            ],
        },
    },
]

WSGI_APPLICATION = 'TireShop.wsgi.application'


# --- База Даних (без змін) ---
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600 # Стабільніше з'єднання
    )
}


# --- Паролі (без змін) ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# --- Мова та Час (без змін) ---
LANGUAGE_CODE = 'uk-ua'
TIME_ZONE = 'Europe/Kiev'
USE_I18N = True
USE_TZ = True


# --- Статичні файли (CSS, JS) ---
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# --- ОСЬ ДРУГА ЧАСТИНА CSS-ФІКСУ ---
# Це каже WhiteNoise, як поводитися з файлами
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# --- Медіа-файли (Фото товарів) (без змін) ---
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# --- Налаштування за замовчуванням (без змін) ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CART_SESSION_ID = 'cart'

# --- Налаштування для Входу/Виходу ---
# Кажемо Django, куди перенаправляти після ВХОDU
LOGIN_REDIRECT_URL = 'users:profile' 
# Кажемо Django, куди перенаправляти після ВИХОДУ
LOGOUT_REDIRECT_URL = 'catalog'
