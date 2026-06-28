from fastapi import APIRouter
from core.redis_client import redis_client
from models.requests import BuyRequest

router= APIRouter()

@router.post("/buy")
def click_buy(req:BuyRequest):
    if BuyRequest.item_id==[]:
        return {"message":"no item in cart"}
    if len(req.item_id)!=len(set(req.item_id)):
        return {"message": "duplicates not allowed"}
    reserved_items=[]
    for i in req.item_id:
        new_val=redis_client.decr(f"stock:{i}")
        if new_val<0:
            for j in reserved_items:
                redis_client.incr(f"stock:{j}")
            return {"message": f"out of stock item {i}"}
        else:
            reserved_items.append(i)
            continue
    return {"message": "success"} 