from fastapi import FastAPI
from app.routes.buy import router as buy_router
from app.routes.stock import router as stock_router
from app.core.redis_client import redis_client

app = FastAPI()

app.include_router(buy_router)
app.include_router(stock_router)

@app.on_event("startup")
def startup():
    redis_client.set("stock:1", 10)
    redis_client.set("stock:2", 12)
    redis_client.set("stock:3", 3)