from fastapi import APIRouter, HTTPException, Depends
from app.core.redis_client import redis_client
from app.dependencies.auth import get_current_user
from app.models.items import ItemRequest

router=APIRouter(prefix="/stock")

@router.get("/")
def get_stock():
    list_items=redis_client.keys("stock:*")
    result={}
    for item in list_items:
        result[item]=redis_client.get(item)
    return result
        
    
@router.post("/set")
def set_stock(item:ItemRequest, user_id:str=Depends(get_current_user)):
    if user_id!="admin":
        raise HTTPException(403, "Admin privileges required")
    redis_client.set(f"stock:{item.id}",item.qty)
    return {"message":"stock updated"} 