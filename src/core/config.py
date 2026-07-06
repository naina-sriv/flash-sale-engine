import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "sales_admin")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
DATABASE_URL=os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://flash_user:flash_pass@flash_postgres:5432/flash_sale",
)
