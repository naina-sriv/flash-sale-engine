from fastapi import APIRouter, Depends
from src.dependencies.auth import require_admin
from src.core.redis_client import redis_client
from src.models.items import ItemRequest

router = APIRouter(prefix="/admin")

@router.post("/flash/add")
def add_item(item: ItemRequest, _ = Depends(require_admin)):
    redis_client.sadd("flash_items", item.id)
    redis_client.set(f"stock:{item.id}", item.qty)
    return {"message": "item added"}

@router.post("/flash/remove")
def remove_item(item: ItemRequest, _ = Depends(require_admin)):
    redis_client.srem("flash_items", item.id)
    return {"message": "item deleted"}

@router.get("/flash/list")
def show_list(_ = Depends(require_admin)):
    list_items = redis_client.smembers("flash_items")
    return list_items