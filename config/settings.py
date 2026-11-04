
"""
Configuração do projeto Easy_Assets (backend).

Local: utiliza SQLite diretamente.

Azure: utiliza SQLite persistente. Configure a variável:
DATABASE_URL=sqlite:////home/data/db.sqlite3
"""

import os
from datetime import timedelta
from pathlib import Path

import environ


BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, True))
environ.Env.read_env(BASE_DIR / ".env")


# ---------------------------------------------------------------------------
# CONFIGURAÇÕES GERAIS
# ---------------------------------------------------------------------------

SECRET_KEY = env(
    "SECRET_KEY",
    default="django-insecure-troque-esta-chave-em-producao"
)

DEBUG = env("DEBUG")

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["*"]
)

# Azure App Service
_azure_hostname = os.environ.get("WEBSITE_HOSTNAME")

if (
    _azure_hostname
    and "*" not in ALLOWED_HOSTS
    and _azure_hostname not in ALLOWED_HOSTS
):
    ALLOWED_HOSTS.append(_azure_hostname)


# ---------------------------------------------------------------------------
# APLICATIVOS INSTALADOS
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Terceiros
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",

    # Aplicativos do EASY ASSET
    "ativos",
    "contas",
    "ordens_manutencao",
    "backups",
]


# ---------------------------------------------------------------------------
# MIDDLEWARE
# ---------------------------------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "config.urls"


# ---------------------------------------------------------------------------
# TEMPLATES
# ---------------------------------------------------------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


WSGI_APPLICATION = "config.wsgi.application"


# ---------------------------------------------------------------------------
# BANCO DE DADOS
# SQLite local e Azure
# ---------------------------------------------------------------------------

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
    )
}


# ---------------------------------------------------------------------------
# VALIDAÇÃO DE SENHAS
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"
    },
]


# ---------------------------------------------------------------------------
# INTERNACIONALIZAÇÃO
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "pt-br"

TIME_ZONE = "America/Sao_Paulo"

USE_I18N = True

USE_TZ = True


# ---------------------------------------------------------------------------
# ARQUIVOS ESTÁTICOS
# ---------------------------------------------------------------------------

STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# DJANGO REST FRAMEWORK
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],

    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],

    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
}


# ---------------------------------------------------------------------------
# SIMPLE JWT
# ---------------------------------------------------------------------------

SIMPLE_JWT = {
    # Tempo de validade do Access Token
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),

    # Tempo de validade do Refresh Token
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),

    # Renovação automática do Refresh Token
    "ROTATE_REFRESH_TOKENS": True,

    # Invalida o Refresh Token anterior após a renovação
    "BLACKLIST_AFTER_ROTATION": True,

}


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

CORS_ALLOW_ALL_ORIGINS = env.bool(
    "CORS_ALLOW_ALL_ORIGINS",
    default=True
)

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[]
)


# ---------------------------------------------------------------------------
# BACKUP DO BANCO (app backups)
# ---------------------------------------------------------------------------

# Pasta dos backups. Fica fora do Git (.gitignore): contém hashes de senha.
BACKUP_DIR = env.path("BACKUP_DIR", default=BASE_DIR / "backups_banco")

# Quantos backups de cada tipo manter (os mais antigos são apagados).
BACKUP_MAX = env.int("BACKUP_MAX", default=10)
