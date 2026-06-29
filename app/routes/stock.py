from fastapi import APIRouter
from app.core.redis_client import redis_client

router=APIRouter(prefix="/stock")

@router.get("/")
def get_stock():
    return {
        "stock:1": redis_client.get("stock:1"),
        "stock:2": redis_client.get("stock:2"),
        "stock:3": redis_client.get("stock:3"),
    }