from fastapi import APIRouter, Depends
from app.core.redis_client import redis_client
from app.models.requests import BuyRequest
from app.dependencies.auth import get_current_user
import time
import asyncio


async def process_payment(user_id: str, item_ids:list):
    print("⏳ Background task started...")   # <-- Add this
    await asyncio.sleep(3)
    print(f"✅ Payment successful for user {user_id} for items {item_ids}")
    
router= APIRouter(prefix="/buy")
flash_inventory=["1","3"]
@router.post("/")
async def click_buy(req:BuyRequest, user_id:str=Depends(get_current_user)):
    if redis_client.exists(f"purchased_flash:{user_id}"):
        return {"message":"only one flash order per customer"}
    lease_key=f"lease:{user_id}"
    if redis_client.exists(lease_key):
        return {"message":f"some item is already reserved for you."}
    if req.item_id==[]:
        return {"message":"no item in cart"}
    if len(req.item_id)!=len(set(req.item_id)):
        return {"message": "duplicates not allowed"}
    count=0
    for i in req.item_id:
        if i in flash_inventory:
            count+=1
    if count>1:
        return {"message":"You can buy only one flash sale item per order"}
    reserved_items=[]
    for i in req.item_id:
        new_val=redis_client.decr(f"stock:{i}")
        if new_val<0:
            for j in reserved_items:
                redis_client.incr(f"stock:{j}")
            redis_client.delete(f"lease:{user_id}")
            return {"message": f"out of stock item {i}"}
        else:
            reserved_items.append(i)
    redis_client.setex(lease_key, 10, "active")
    if count==1:
        redis_client.setex(f"purchased_flash:{user_id}",89400,"active")
    asyncio.create_task(process_payment( user_id, req.item_id))
    return {"message": "reserved"} 