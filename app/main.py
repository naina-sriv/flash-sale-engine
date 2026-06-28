from fastapi import FastAPI
# from app.db import AsyncSessionLocal
# from sqlalchemy import text
from pydantic import BaseModel

app=FastAPI()

@app.get("/")
def root():
    return {"message": "flash-sale-engine"}

# @app.get("/health/db")
# async def health_db():
#     try:
#         async with AsyncSessionLocal() as session:
#             result= await session.execute(text("SELECT 1"))
#             return {"status":"connected","result":result.scalar()}
#     except Exception as e:
#         return {"status":"error","message":str(e)}

#format [{user_id: string, item_id: list[string]}]

class BuyRequest(BaseModel):
    user_id: str
    item_id: list[str]
    
stock={"1": 10,"2":12, "3":3}
@app.post("/buy")
def click_buy(res:BuyRequest):
    new_stock={}
    if res.item_id==[]:
        return {"message":"no item in cart"}
    if len(res.item_id)!=len(set(res.item_id)):
        return {"message": "duplicates not allowed"}
    for i in res.item_id:
        new_stock[i]=stock[i]-1
        if new_stock[i]<0:
            return {"message": f"out of stock item {i}"}
        else:
            continue
    for i in new_stock:
        stock[i]=new_stock[i]
    return stock
        
        
        