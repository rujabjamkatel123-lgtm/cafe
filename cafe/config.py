import os


# =========================================================
# FLASK SECRET KEY
# =========================================================

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "dev-secret-key-change-in-production"
)

SECURE_SESSION_COOKIE = os.environ.get(
    "SECURE_SESSION_COOKIE",
    "0"  # Local HTTP development; set SECURE_SESSION_COOKIE=1 on HTTPS production
).lower() in {"1", "true", "yes", "on"}

# Public origin used in printed customer QR codes. Set this to the deployed
# HTTPS site URL, for example: https://your-restaurant.vercel.app
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")


# =========================================================
# MYSQL DATABASE CONFIGURATION
# =========================================================

MYSQL_HOST = os.environ.get("MYSQL_HOST")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE")