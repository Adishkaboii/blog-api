from settings import conf
from settings.base import *

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": conf.DB_NAME,
        "USER": conf.DB_USER,
        "PASSWORD": conf.DB_PASSWORD,
        "HOST": conf.DB_HOST,
        "PORT": conf.DB_PORT,
    }
}