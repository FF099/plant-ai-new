from pathlib import Path
from dotenv import load_dotenv
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file (สำหรับตอนรันบนเครื่องตัวเองเท่านั้น
# บน Railway ค่าจะมาจาก Variables ในหน้าเว็บโดยตรง ไม่ใช้ไฟล์ .env)
load_dotenv(BASE_DIR / '.env')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-$8(&j6qml#gaed^hu_%sebbc*&%v8p@*#7)+huo^%6sw7_=g9k')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# บน Railway ให้ตั้ง ALLOWED_HOSTS ใน Variables เป็นโดเมนจริง เช่น
# xxx.up.railway.app (คั่นด้วย comma ถ้ามีหลายโดเมน)
_allowed_hosts_env = os.getenv('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_env.split(',') if h.strip()]
if not ALLOWED_HOSTS:
    # fallback เผื่อยังไม่ได้ตั้งค่า env — ครอบคลุมโดเมน Railway ทุกแบบ
    ALLOWED_HOSTS = ['.railway.app', 'localhost', '127.0.0.1']

# CSRF trusted origins ต้องมี scheme (https://) นำหน้าเสมอ
# บน Railway ให้ตั้ง Variable ชื่อ CSRF_TRUSTED_ORIGINS เป็นโดเมนจริง เช่น
# https://web-production-449d6.up.railway.app (คั่นด้วย comma ถ้ามีหลายโดเมน)
_csrf_trusted_env = os.getenv('CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_trusted_env.split(',') if o.strip()]
if not CSRF_TRUSTED_ORIGINS:
    # fallback เผื่อยังไม่ได้ตั้งค่า env
    CSRF_TRUSTED_ORIGINS = [
        'https://*.railway.app',
        'https://web-production-449d6.up.railway.app',
    ]

# Railway ใช้ reverse proxy (SSL terminate ที่ proxy แล้วส่ง HTTP เข้ามาในแอปภายใน)
# ต้องบอก Django ว่า request ที่มี header นี้ให้ถือว่าเป็น HTTPS ไม่งั้น CSRF/Session cookie จะพัง
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# บังคับ cookie เป็น secure เมื่อไม่ใช่โหมด DEBUG (เช่นตอน deploy จริงบน Railway)
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'PlantAI_App',
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

ROOT_URLCONF = 'PlantAI.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


WSGI_APPLICATION = 'PlantAI.wsgi.application'


# Database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation

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


# Internationalization

LANGUAGE_CODE = 'th-th'

TIME_ZONE = 'Asia/Bangkok'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
# โฟลเดอร์ปลายทางที่ collectstatic จะรวมไฟล์ static ทั้งหมดไปไว้ (Railway/production ใช้ตัวนี้)
STATIC_ROOT = BASE_DIR / 'staticfiles'
# ให้ whitenoise บีบอัดและ cache ไฟล์ static ให้อัตโนมัติ
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Default primary key field type

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Authentication Redirects

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/management/'
LOGOUT_REDIRECT_URL = '/'

from django.contrib.messages import constants as messages_constants

MESSAGE_TAGS = {
    messages_constants.DEBUG: 'secondary',
    messages_constants.INFO: 'info',
    messages_constants.SUCCESS: 'success',
    messages_constants.WARNING: 'warning',
    messages_constants.ERROR: 'danger',   # Django ใช้ 'error' แต่ Bootstrap ใช้ 'alert-danger'
}