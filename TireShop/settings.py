import os
import dj_database_url
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-a_dummy_key_for_now_!@#$')

# --- ЛОГІКА DEBUG ТА ДОМЕНІВ ---
# Якщо ми на Render:
if 'RENDER' in os.environ:
    # На живому сайті вимикаємо DEBUG (безпека + швидкість)
    DEBUG = False 
    ALLOWED_HOSTS = [
        os.environ.get('RENDER_EXTERNAL_HOSTNAME'), # Адреса від Render (tireshop...onrender.com)
        'r16.com.ua',       # <--- ВАШ НОВИЙ ДОМЕН
        'www.r16.com.ua',   # <--- ВЕРСІЯ З WWW
    ]
else:
    # Вдома на комп'ютері
    DEBUG = True
    ALLOWED_HOSTS = ['*']

# --- ДОДАТКИ ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps', # Для карти сайту (Google)
    
    'store.apps.StoreConfig', 
    'users.apps.UsersConfig', 
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware', 
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'TireShop.urls' 

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
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

DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=0 # Щоб база не "відвалювалася"
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'uk-ua'
TIME_ZONE = 'Europe/Kyiv'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') 
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Стабільна версія для статики
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CART_SESSION_ID = 'cart'

LOGIN_REDIRECT_URL = 'users:profile' 
LOGOUT_REDIRECT_URL = 'catalog'

GSPREAD_CREDENTIALS_PATH = '/etc/secrets/credentials.json'
