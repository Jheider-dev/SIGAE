"""
Configuración de Django para el proyecto SIGAE.

Desarrollado bajo estándares PEP 8 y adaptado para el uso de variables de
entorno y base de datos PostgreSQL para la Academia Preuniversitaria Euler.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Ruta raíz del proyecto (BASE_DIR)
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar variables de entorno desde el archivo .env
load_dotenv(BASE_DIR / '.env')

# Clave secreta obtenida desde variables de entorno
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-kn_-mr^9-!j$e^cy!d!v02sgat7kvywb7qa#4xd=qgj1h@(a_7'
)

# Modo de depuración (Debug)
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']


# Definición de Aplicaciones
# ------------------------------------------------------------------------------

LOCAL_APPS = [
    'autenticacion',
    'academico',
    'simulacros',
    'reportes',
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Aplicaciones locales del sistema SIGAE
    *LOCAL_APPS,
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

# Configuración de Proxy Inverso y SSL (requerido para Vercel y entornos en la nube)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Orígenes confiables para CSRF
CSRF_TRUSTED_ORIGINS = [
    'https://*.vercel.app',
    'https://*.now.sh',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# Agregar automáticamente URLs generadas por Vercel si existen
if os.environ.get('VERCEL_URL'):
    CSRF_TRUSTED_ORIGINS.append(f"https://{os.environ.get('VERCEL_URL')}")
if os.environ.get('VERCEL_PROJECT_PRODUCTION_URL'):
    CSRF_TRUSTED_ORIGINS.append(f"https://{os.environ.get('VERCEL_PROJECT_PRODUCTION_URL')}")

# Soporte para orígenes personalizados desde variables de entorno
custom_csrf_origins = os.environ.get('CSRF_TRUSTED_ORIGINS')
if custom_csrf_origins:
    CSRF_TRUSTED_ORIGINS.extend([
        origin.strip() for origin in custom_csrf_origins.split(',') if origin.strip()
    ])

# Configuración de Cookies para producción / Vercel
if not DEBUG or os.environ.get('VERCEL'):
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SAMESITE = 'Lax'

ROOT_URLCONF = 'sigae.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'sigae.wsgi.application'


# Configuración de Base de Datos Adaptable (Cloud PostgreSQL / Local / Vercel)
# ------------------------------------------------------------------------------

DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    try:
        import dj_database_url
        DATABASES = {
            'default': dj_database_url.parse(
                DATABASE_URL,
                conn_max_age=0,
                ssl_require=True
            )
        }
        DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True
    except Exception:
        import urllib.parse as urlparse
        url = urlparse.urlparse(DATABASE_URL)
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': url.path[1:] if url.path else 'postgres',
                'USER': url.username or 'postgres',
                'PASSWORD': url.password or '',
                'HOST': url.hostname,
                'PORT': str(url.port or 5432),
                'OPTIONS': {
                    'sslmode': 'require',
                },
                'CONN_MAX_AGE': 0,
                'DISABLE_SERVER_SIDE_CURSORS': True,
            }
        }
elif os.environ.get('DB_HOST') and os.environ.get('DB_HOST') != 'localhost':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'sigae_euler_db'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'OPTIONS': {
                'sslmode': 'require',
            },
        }
    }
else:
    if os.environ.get('VERCEL'):
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': '/tmp/db.sqlite3',
            }
        }
    else:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': os.environ.get('DB_NAME', 'sigae_euler_db'),
                'USER': os.environ.get('DB_USER', 'postgres'),
                'PASSWORD': os.environ.get('DB_PASSWORD', '76925540'),
                'HOST': os.environ.get('DB_HOST', 'localhost'),
                'PORT': os.environ.get('DB_PORT', '5432'),
            }
        }




# Validadores de Contraseña
# ------------------------------------------------------------------------------

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


# Internacionalización
# ------------------------------------------------------------------------------

LANGUAGE_CODE = 'es-pe'

TIME_ZONE = 'America/Lima'

USE_I18N = True

USE_TZ = True


# Archivos Estáticos (CSS, JavaScript, Images)
# ------------------------------------------------------------------------------

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
WHITENOISE_USE_FINDERS = True

# Tipo por defecto para llaves primarias auto-incrementables
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configuración del modelo de usuario personalizado
AUTH_USER_MODEL = 'autenticacion.Usuario'

# Configuración de Logging y Auditoría de Seguridad
# ------------------------------------------------------------------------------
if os.environ.get('VERCEL'):
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '[{asctime}] [{levelname}] {message}',
                'style': '{',
            },
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
        },
        'loggers': {
            'sigae.audit': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
        },
    }
else:
    LOG_DIR = os.path.join(BASE_DIR, 'var', 'log', 'sigae')
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except Exception:
        LOG_DIR = '/tmp'
    LOG_FILE = os.path.join(LOG_DIR, 'audit.log')

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '[{asctime}] [{levelname}] {message}',
                'style': '{',
            },
        },
        'handlers': {
            'audit_file': {
                'level': 'INFO',
                'class': 'logging.FileHandler',
                'filename': LOG_FILE,
                'formatter': 'verbose',
                'encoding': 'utf-8',
            },
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
        },
        'loggers': {
            'sigae.audit': {
                'handlers': ['audit_file', 'console'],
                'level': 'INFO',
                'propagate': False,
            },
        },
    }
