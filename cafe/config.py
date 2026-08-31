import os


# =========================================================
# FLASK SECRET KEY
# =========================================================

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "dev-secret-key-change-in-production"
)


# =========================================================
# SESSION COOKIE
# =========================================================

SECURE_SESSION_COOKIE = os.environ.get(
    "SECURE_SESSION_COOKIE",
    "0"
).lower() in {"1", "true", "yes", "on"}


# =========================================================
# PUBLIC WEBSITE URL
# =========================================================

PUBLIC_BASE_URL = os.environ.get(
    "PUBLIC_BASE_URL",
    ""
).strip().rstrip("/")


# =========================================================
# MYSQL DATABASE CONFIGURATION
# =========================================================

MYSQL_HOST = os.environ.get(
    "MYSQL_HOST",
    "localhost"
)

MYSQL_PORT = int(
    os.environ.get(
        "MYSQL_PORT",
        "3306"
    )
)

MYSQL_USER = os.environ.get(
    "MYSQL_USER",
    "root"
)

MYSQL_PASSWORD = os.environ.get(
    "MYSQL_PASSWORD",
    ""
)

MYSQL_DATABASE = os.environ.get(
    "MYSQL_DATABASE",
    "cafe"
)