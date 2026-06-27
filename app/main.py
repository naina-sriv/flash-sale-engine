from fastapi import FastAPI
from db import AsyncSessionLocal
from sqlalchemy import text

app=FastAPI()

@app.get("/")
def root():
    return {"message": "flash-sale-engine"}

@app.get("/health/db")
async def health_db():
    try:
        async with AsyncSessionLocal() as session:
            result= await session.execute(text("SELECT 1"))
            return {"status":"connected","result":result.scalar()}
    except Exception as e:
        return {"status":"error","message":str(e)}