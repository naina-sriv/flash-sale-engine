from fastapi import FastAPI
from src.routes.buy import router as buy_router
from src.routes.stock import router as stock_router
from src.routes.auth import router as auth_router
from src.core.redis_client import redis_client
from src.routes.admin import router as admin_router
from src.core.db import engine, Base
import src.schema.db_models
app = FastAPI()

app.include_router(buy_router)
app.include_router(stock_router)
app.include_router(auth_router)
app.include_router(admin_router)


@app.on_event("startup")
async def startup():
    # DB is optional for the flash-sale Redis flow; don't crash the whole API.
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        # Keep startup alive so Redis routes (/buy/, /stock/, /auth/) can work.
        print(f"[startup] DB init failed (continuing): {type(e).__name__}: {e}")


    # Seed Redis
    redis_client.set("stock:1", 10)
    redis_client.set("stock:2", 12)
    redis_client.set("stock:3", 3)
    redis_client.sadd("flash_items", "1", "3")
