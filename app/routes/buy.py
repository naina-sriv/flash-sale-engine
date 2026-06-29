from fastapi import APIRouter, Depends
from app.core.redis_client import redis_client
from app.models.requests import BuyRequest
from app.dependencies.auth import get_current_user

router= APIRouter(prefix="/buy")

@router.post("/")
def click_buy(req:BuyRequest, user_id:str=Depends(get_current_user)):
    if req.item_id==[]:
        return {"message":"no item in cart"}
    if len(req.item_id)!=len(set(req.item_id)):
        return {"message": "duplicates not allowed"}
    reserved_items=[]
    for i in req.item_id:
        lease_key=f"lease:{user_id}:{i}"
        if redis_client.exists(lease_key):
            return {"message":f"the item {i} is already reserved for you."}
        new_val=redis_client.decr(f"stock:{i}")
        if new_val<0:
            for j in reserved_items:
                redis_client.incr(f"stock:{j}")
                redis_client.delete(f"lease:{user_id}:{j}")
            return {"message": f"out of stock item {i}"}
        else:
            redis_client.setex(lease_key,300,"active")
            reserved_items.append(i)
            continue
    return {"message": "success"} 