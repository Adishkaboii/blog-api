from pathlib import Path

from decouple import Config, RepositoryEnv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / "settings" / ".env"

config = Config(RepositoryEnv(ENV_FILE))

SECRET_KEY = config("BLOG_SECRET_KEY")
DEBUG = config("BLOG_DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config(
    "BLOG_ALLOWED_HOSTS",
    default="",
    cast=lambda value: [
        host.strip() for host in value.split(",") if host.strip()
    ],
)

DB_NAME = config("BLOG_DB_NAME", default="blog")
DB_USER = config("BLOG_DB_USER", default="postgres")
DB_PASSWORD = config("BLOG_DB_PASSWORD", default="")
DB_HOST = config("BLOG_DB_HOST", default="localhost")
DB_PORT = config("BLOG_DB_PORT", default="5432")