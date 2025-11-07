import os
import dj_database_url
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# --- Ключові налаштування безпеки ---

# !!! ВАЖЛИВО: Це ми змінимо на Render. Поки залишаємо так.
SECRET_KEY = 'django-insecure-a_dummy_key_for_now_!@#$%'

# !!! ВАЖЛИВО: Render автоматично змінить це на False.
# Коли DEBUG = True, Django показує детальні помилки.
DEBUG = True

# Тут буде адреса вашого сайту на Render (наприклад, 'tireshop.onrender.com')
# '*' означає "дозволити будь-які адреси" (небезпечно, але просто для старту)
ALLOWED_HOSTS = ['*']


# --- Додатки (Apps) ---
# Тут ми "вмикаємо" наші додатки: магазин та кабінет.

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Наші додатки, які ми створили
    'store.apps.StoreConfig', # Повна назва з файлу apps.py
    'users.apps.UsersConfig', # Повна назва з файлу apps.py
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', # Важливо для кошика
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'TireShop.urls' # Посилання на головний файл urls.py


# --- Шаблони (HTML) ---
# Тут ми кажемо Django, де шукати HTML-файли

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Ми вказали Django шукати шаблони всередині кожного додатка
        # (store/templates/store/, users/templates/users/)
        'DIRS': [], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                
                # Наш процесор, щоб кошик був доступний на всіх сторінках
                'store.context_processors.cart',
            ],
        },
    },
]

WSGI_APPLICATION = 'TireShop.wsgi.application'


# --- База Даних (Дуже важливо для Render) ---
# Цей код автоматично підключиться до бази даних PostgreSQL на Render,
# використовуючи "секретну" адресу DATABASE_URL.

DATABASES = {
    'default': dj_database_url.config(
        # Якщо він не знайде DATABASE_URL, він створить локальний файл 'db.sqlite3'
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}'
    )
}


# --- Паролі ---

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# --- Мова та Час ---

LANGUAGE_CODE = 'uk-ua' # Українська мова

TIME_ZONE = 'Europe/Kiev' # Київський час

USE_I18N = True

USE_TZ = True


# --- Статичні файли (CSS, JS) ---
# Це те, що збирає наш build.sh

STATIC_URL = 'static/'
# Це папка, КУДИ Render збере всі статичні файли (style.css)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') 


# --- Медіа-файли (Фото товарів) ---
# Це фото, які ви будете завантажувати через адмінку

MEDIA_URL = '/media/'
# Це папка, ДЕ будуть зберігатися ці фото
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# --- Налаштування за замовчуванням ---

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# --- Наш ID для сесії кошика ---
CART_SESSION_ID = 'cart'
