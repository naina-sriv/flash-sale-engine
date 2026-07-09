from fastapi import APIRouter, Depends

from src.core.redis_client import redis_client
from src.dependencies.auth import require_admin
from src.models.items import ItemRequest
from src.models.responses import AdminFlashResponse, FlashListResponse

router = APIRouter(prefix="/admin")


@router.post("/flash/add", response_model=AdminFlashResponse)
def add_item(item: ItemRequest, _=Depends(require_admin)):
    redis_client.sadd("flash_items", item.id)
    redis_client.set(f"stock:{item.id}", item.qty)
    return AdminFlashResponse(message="item added")


@router.post("/flash/remove", response_model=AdminFlashResponse)
def remove_item(item: ItemRequest, _=Depends(require_admin)):
    redis_client.srem("flash_items", item.id)
    return AdminFlashResponse(message="item deleted")


@router.get("/flash/list", response_model=FlashListResponse)
def show_list(_=Depends(require_admin)):
    list_items = list(redis_client.smembers("flash_items"))
    return FlashListResponse(flash_items=list_items)
