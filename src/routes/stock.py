from fastapi import APIRouter, HTTPException, Depends
from src.core.redis_client import redis_client
from src.dependencies.auth import require_admin
from src.models.items import ItemRequest

router=APIRouter(prefix="/stock")

@router.get("/")
def get_stock():
    list_items=redis_client.keys("stock:*")
    result={}
    for item in list_items:
        result[item]=redis_client.get(item)
    return result
        
    
@router.post("/set")
async def set_stock(item: ItemRequest, _ = Depends(require_admin)):
    redis_client.set(f"stock:{item.id}", item.qty)
    return {"message": "stock updated"}