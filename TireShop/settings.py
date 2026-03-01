import os
import dj_database_url
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-a_dummy_key_for_now_!@#$')

# --- ЛОГІКА DEBUG ТА ДОМЕНІВ ---
if 'RENDER' in os.environ:
    DEBUG = False 
    
    ALLOWED_HOSTS = [
        os.environ.get('RENDER_EXTERNAL_HOSTNAME'), 
        'r16.com.ua',        
        'www.r16.com.ua',    
    ]
    
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
else:
    DEBUG = True
    ALLOWED_HOSTS = ['*']

# --- ДОДАТКИ ---
INSTALLED_APPS = [
    'jazzmin',  # 🔥 СУЧАСНА CRM-АДМІНКА (Має бути ПЕРЕД django.contrib.admin)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps', 
    
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
        conn_max_age=600 
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'uk'
TIME_ZONE = 'Europe/Kyiv'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') 
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
WHITENOISE_MANIFEST_STRICT = False

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CART_SESSION_ID = 'cart_final_fix'

LOGIN_REDIRECT_URL = 'users:profile' 
LOGOUT_REDIRECT_URL = 'catalog'

GSPREAD_CREDENTIALS_PATH = '/etc/secrets/credentials.json'

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

# ==========================================
# 🔥 НАЛАШТУВАННЯ CRM (JAZZMIN) 🔥
# ==========================================
JAZZMIN_SETTINGS = {
    "site_title": "R16 CRM",
    "site_header": "R16.ua",
    "site_brand": "Управління R16",
    "welcome_sign": "Вхід у CRM систему R16.ua",
    
    # Переклад головних розділів меню
    "custom_app_labels": {
        "store": "Керування Магазином",
        "auth": "Права доступу",
        "users": "Клієнти",
    },
    
    "search_model": ["store.Order", "store.Product"],
    "show_sidebar": True,
    "navigation_expanded": True,
    
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "store.Order": "fas fa-shopping-cart",
        "store.Product": "fas fa-box",
        "store.Brand": "fas fa-copyright",
        "store.SiteSettings": "fas fa-cogs",
        "store.SiteBanner": "fas fa-images",
        "store.AboutImage": "fas fa-camera",
    },
    
    "order_with_respect_to": ["store.Order", "store.Product", "store.Brand", "store.SiteBanner"],
}
