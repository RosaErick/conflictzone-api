"""Configuração do Django (core). Tudo sensível vem do ambiente."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

# Caminhos do projeto: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ('1', 'true', 'yes')


# Padrão True para dev local; em produção defina DJANGO_DEBUG=False.
DEBUG = env_bool('DJANGO_DEBUG', True)

# Fallback inseguro só é permitido em dev; produção exige DJANGO_SECRET_KEY.
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-only-do-not-use-in-production'
    else:
        raise ImproperlyConfigured('DJANGO_SECRET_KEY must be set when DEBUG=False')

# Lista separada por vírgula via env (ex.: "1.2.3.4,api.example.com"); somada aos padrões.
_default_hosts = ['127.0.0.1', 'localhost', '.vercel.app']
_env_hosts = [h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', '').split(',') if h.strip()]
ALLOWED_HOSTS = _default_hosts + _env_hosts


# Aplicações

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'rest_framework',
    'drf_spectacular',
    'corsheaders',
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'api.middleware.RequestLogMiddleware',
]

ROOT_URLCONF = 'core.urls'

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

WSGI_APPLICATION = 'core.wsgi.app'
FOGO_CRUZADO_EMAIL = os.getenv('FOGO_CRUZADO_EMAIL')
FOGO_CRUZADO_PASSWORD = os.getenv('FOGO_CRUZADO_PASSWORD')
# UUID do estado do Rio de Janeiro (era hardcoded no serviço); sobrescreva via env.
FOGO_CRUZADO_STATE_ID = os.getenv(
    'FOGO_CRUZADO_STATE_ID', 'b112ffbe-17b3-4ad0-8f2a-2038745d1d14'
)
# Idade máxima da última ingestão antes de /health e endpoints darem 503.
# 96h = cadência manual atual (~3 dias + 1 de folga); só pega "nunca ingeriu" ou
# "abandonado". Baixe para perto da janela incremental quando o cron automático rodar.
INGESTION_MAX_AGE_HOURS = int(os.getenv('INGESTION_MAX_AGE_HOURS', '96'))
# Janela incremental padrão (em dias) quando sync_occurrences roda sem datas.
INGESTION_DEFAULT_DAYS = int(os.getenv('INGESTION_DEFAULT_DAYS', '3'))


# CORS: allowlist explícita via env em prod; aberto só em dev local.
# ponytail: lista por env resolve; aperte com CORS_ALLOWED_ORIGINS em produção.
_cors_origins = [o.strip() for o in os.getenv('CORS_ALLOWED_ORIGINS', '').split(',') if o.strip()]
if _cors_origins:
    CORS_ALLOWED_ORIGINS = _cors_origins
else:
    CORS_ALLOW_ALL_ORIGINS = DEBUG


# Banco — PostgreSQL + PostGIS é a fonte de verdade (geoespacial é não-negociável).
# Todos os parâmetros vêm do ambiente; nenhum segredo no código.
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.getenv('POSTGRES_DB', 'conflictzone'),
        'USER': os.getenv('POSTGRES_USER', 'conflictzone'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'conflictzone'),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}


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


LANGUAGE_CODE = 'en-us'

# Persiste tudo em UTC tz-aware; agrupa as séries em horário local (abaixo).
TIME_ZONE = 'UTC'

# Fuso usado para agrupar séries dia/semana/mês — o "dia" tem que bater com o do usuário.
LOCAL_TZ = os.getenv('ANALYTICS_TZ', 'America/Sao_Paulo')

USE_I18N = True

USE_TZ = True


# Arquivos estáticos
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# drf-spectacular
SPECTACULAR_SETTINGS = {
    'TITLE': 'ConflictZone API',
    'DESCRIPTION': 'API for conflict/violence occurrence data from Fogo Cruzado',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# Logging: um handler para stdout, amigável a container. Substitui todo print().
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '%(asctime)s %(levelname)s %(name)s %(message)s'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'root': {'handlers': ['console'], 'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO')},
}
