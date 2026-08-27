"""
Configuração do projeto Easy_Assets (backend).

Local: roda com SQLite direto, sem precisar configurar nada.
Azure: o professor definiu que o banco de produção também é SQLite. Para
que o arquivo do banco sobreviva a cada novo deploy, aponte-o para uma
pasta fora de /home/site/wwwroot (que é substituída a cada deploy) — defina
na Azure a variável de ambiente:
  DATABASE_URL=sqlite:////home/data/db.sqlite3
(repare nas 4 barras: 3 do esquema "sqlite://" + 1 do caminho absoluto).
Veja o .env.example e o README (seção "Deploy na Azure").
"""

import os
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, True))
environ.Env.read_env(BASE_DIR / ".env")  # não falha se o arquivo não existir

SECRET_KEY = env("SECRET_KEY", default="django-insecure-troque-esta-chave-em-producao")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

# A Azure App Service expõe o nome do site nessa variável de ambiente
# automaticamente (ex.: "easyassets-backend.azurewebsites.net") — isso
# libera esse domínio sem precisar configurar ALLOWED_HOSTS manualmente.
_azure_hostname = os.environ.get("WEBSITE_HOSTNAME")
if _azure_hostname and "*" not in ALLOWED_HOSTS and _azure_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_azure_hostname)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # terceiros
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    # apps do projeto
    "ativos",
    "contas",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serve os arquivos estáticos do /admin na Azure
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
# Banco de dados: SQLite sempre (local e na Azure, por decisão do professor).
# Na Azure, DATABASE_URL aponta pra um caminho persistente fora de wwwroot —
# veja o comentário no topo do arquivo e o README.
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # onde o "collectstatic" junta os arquivos para a Azure servir
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework + autenticação JWT
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

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# ---------------------------------------------------------------------------
# CORS — libera o painel web (Vue) e o app mobile (Flutter) a consumir a API.
# Em desenvolvimento libera tudo; em produção troque por CORS_ALLOWED_ORIGINS
# com a URL real do painel web (o app Flutter não é afetado por CORS).
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=True)
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
