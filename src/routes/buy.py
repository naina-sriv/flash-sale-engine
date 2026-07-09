from fastapi import APIRouter, Depends
from src.core.redis_client import redis_client
from src.models.requests import BuyRequest
from src.dependencies.auth import get_current_user
import time
import asyncio
from src.schema.db_models import Order
from src.core.db import AsyncSessionLocal
from datetime import datetime


async def process_payment(user_id: str, item_ids:list):
    print("⏳ Background task started...")   # <-- Add this
    await asyncio.sleep(3)
    print(f"✅ Payment successful for user {user_id} for items {item_ids}")
    async with AsyncSessionLocal() as session:
        for item_id in item_ids:
                new_order = Order(
                user_id=int(user_id),
                product_id=int(item_id),
                quantity=1,
                price_at_purchase=10.0,  # placeholder — later, fetch from products table
                status="paid"
            )
        session.add(new_order)
        await session.commit()
        print(f"✅ Order(s) saved for user {user_id}")
    
router= APIRouter(prefix="/buy")
@router.post("/")
async def click_buy(req:BuyRequest, user_id:str=Depends(get_current_user)):
    lease_key=f"lease:{user_id}"
    if redis_client.exists(lease_key):
        return {"message":f"some item is already reserved for you."}
    if req.item_id==[]:
        return {"message":"no item in cart"}
    if len(req.item_id)!=len(set(req.item_id)):
        return {"message": "duplicates not allowed"}
    count=0
    for i in req.item_id:
        if redis_client.sismember("flash_items", i):
            if redis_client.exists(f"purchased_flash:{user_id}"):
                return {"message":"only one flash order per customer"}
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