import os
from dotenv import load_dotenv

load_dotenv()


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_env_config():
    return {
        "mysql_host": os.getenv("MYSQL_HOST"),
        "mysql_port": int(os.getenv("MYSQL_PORT", "3306")),
        "mysql_user": os.getenv("MYSQL_USER"),
        "mysql_password": os.getenv("MYSQL_PASSWORD"),
        "mysql_database": os.getenv("MYSQL_DATABASE"),
        "mysql_ssl": _bool(os.getenv("MYSQL_SSL"), default=False),
        "mysql_ssl_reject_unauthorized": _bool(
            os.getenv("MYSQL_SSL_REJECT_UNAUTHORIZED"), default=True
        ),
    }
