from fastapi import FastAPI

from src.core.redis_client import redis_client
from src.routes.admin import router as admin_router
from src.routes.auth import router as auth_router
from src.routes.buy import router as buy_router
from src.routes.stock import router as stock_router

app = FastAPI()

app.include_router(buy_router)
app.include_router(stock_router)
app.include_router(auth_router)
app.include_router(admin_router)


import asyncio

from alembic import command
from alembic.config import Config
from src.core.logger import logger


@app.on_event("startup")
async def startup():
    # DB is optional for the flash-sale Redis flow; don't crash the whole API.
    try:

        def run_upgrade():
            alembic_cfg = Config("alembic.ini")
            command.upgrade(alembic_cfg, "head")

        await asyncio.to_thread(run_upgrade)
    except Exception as e:
        # Keep startup alive so Redis routes (/buy/, /stock/, /auth/) can work.
        logger.error(
            f"[startup] DB migration failed (continuing): {type(e).__name__}: {e}"
        )

    # Seed Redis
    redis_client.set("stock:1", 10)
    redis_client.set("stock:2", 12)
    redis_client.set("stock:3", 3)
    redis_client.sadd("flash_items", "1", "3")
