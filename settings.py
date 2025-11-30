from pathlib import Path
#это строчка чтобы узнать работает ли CI/CD
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-7@uc%1l9bl23z)jz1^cdl%kd#+b-x3rhryb484t4go2!333om5'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '195.133.194.73', '10.47.109.140', 'test-vapp-03.sgp.ru', 'sco1-vapp-04.sgp.ru']
#ALLOWED_HOSTS = ['*']

CORS_ORIGIN_ALLOW_ALL = False
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://195.133.194.73",
]

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_celery_results',
    'corsheaders',
    'rest_framework',
    'app'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'mailservice.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mailservice.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'test-vapp-03.sgp.ru',
        'PORT': '5432',
        #'HOST': 'localhost',
        #'PORT': '5432',
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'ru-ru'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Cellery
CELERY_BROKER_URL = 'amqp://user:pass@mail-service-rabbitmq-1:5672//'
#CELERY_BROKER_URL = 'amqp://user:pass@localhost:5672//'

CELERY_RESULT_BACKEND = 'rpc://'
CELERY_CACHE_BACKEND = 'django-cache'

#smtp или почта

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'sco1-msg-01.sgp.ru'  # SMTP-сервер TimeWeb
EMAIL_PORT = 587  # Порт для TLS (может быть 465 для SSL)
#EMAIL_USE_TLS = True  # Использовать TLS (для порта 587)
# EMAIL_USE_SSL = True  # Если используете порт 465, раскомментируйте эту строку и закомментируйте EMAIL_USE_TLS
EMAIL_HOST_USER = 'srv_mail_service'  # Ваш email на TimeWeb
EMAIL_HOST_PASSWORD = 'V_T@Dyq?nvVVf3gQy}vWe-9VE{?,Ke'  # Пароль от почты
DEFAULT_FROM_EMAIL = 'admin@surgut.gazprom.ru'  # Email отправителя по умолчанию
SERVER_EMAIL = 'admin@surgut.gazprom.ru'  # Email для ошибок сервера