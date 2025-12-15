import os
import dj_database_url
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-a_dummy_key_for_now_!@#$')

# --- ЛОГІКА DEBUG ТА ДОМЕНІВ ---
# Якщо ми на Render:
if 'RENDER' in os.environ:
    # 🔥 НА ЖИВОМУ САЙТІ ВИМИКАЄМО DEBUG (Критично для швидкості та кешу)
    DEBUG = False 
    
    ALLOWED_HOSTS = [
        os.environ.get('RENDER_EXTERNAL_HOSTNAME'), # Адреса від Render
        'r16.com.ua',        # ВАШ ДОМЕН
        'www.r16.com.ua',    # WWW ВЕРСІЯ
    ]
    
    # 🔥 БЕЗПЕКА І HTTPS (Google це любить)
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 рік
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
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
    # 'whitenoise.runserver_nostatic', # Можна додати для тесту локально, але не обов'язково
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # 🔥 WHITENOISE (Має бути відразу після Security)
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
        conn_max_age=600 # Тримати з'єднання 10 хв (швидше для PostgreSQL)
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

# --- СТАТИКА (CSS, JS, IMAGES) ---
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') 
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# 🔥 МАКСИМАЛЬНА ОПТИМІЗАЦІЯ WHITENOISE 🔥
# CompressedManifest... стискає файли (Gzip/Brotli) і додає хеш до імені.
# Це дозволяє браузеру кешувати їх "назавжди" (вирішує проблему PageSpeed про кеш).
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CART_SESSION_ID = 'cart'

LOGIN_REDIRECT_URL = 'users:profile' 
LOGOUT_REDIRECT_URL = 'catalog'

GSPREAD_CREDENTIALS_PATH = '/etc/secrets/credentials.json'

# --- ТЕЛЕГРАМ БОТ ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
