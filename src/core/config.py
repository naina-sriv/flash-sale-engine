import os
import warnings

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = "sales_admin"
    warnings.warn(
        "SECRET_KEY not set in environment — falling back to an insecure default. "
        "Set SECRET_KEY in your .env before deploying anywhere real.",
        stacklevel=2,
    )

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://flash_user:flash_pass@flash_postgres:5432/flash_sale",
)
