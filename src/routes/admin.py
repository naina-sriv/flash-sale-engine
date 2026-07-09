from fastapi import APIRouter, HTTPException, Depends
from src.dependencies.auth import get_current_user, require_admin
from src.core.redis_client import redis_client
from src.models.items import ItemRequest

router=APIRouter(prefix="/admin")

@router.post("/flash/add")
def add_item(item: ItemRequest, user_id:str=Depends(get_current_user), _ = Depends(require_admin)):
    if user_id!="admin":
        raise HTTPException(403, "Admin privileges required")
    redis_client.sadd("flash_items", item.id)
    redis_client.set(f"stock:{item.id}",item.qty)
    return {"message": "item added"}

@router.post("/flash/remove")
def remove_item(item:ItemRequest, user_id:str=Depends(get_current_user),_ = Depends(require_admin)):
    if user_id!="admin":
        raise HTTPException(403, "Admin privileges required")
    redis_client.srem("flash_items", item.id)
    return {"message":"item deleted"}

@router.get("/flash/list")
def show_list(user_id:str=Depends(get_current_user),_ = Depends(require_admin)):
    if user_id!="admin":
        raise HTTPException(403, "Admin privileges required")
    list_items=redis_client.smembers("flash_items")
    return list_items

            
    
    
