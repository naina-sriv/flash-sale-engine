from fastapi import APIRouter, HTTPException
from src.models.requests import LoginRequest
from src.core.config import SECRET_KEY, ALGORITHM
import jwt
from sqlalchemy import select
from src.core.db import AsyncSessionLocal
from src.schema.db_models import User
import bcrypt

router = APIRouter(prefix="/auth")

@router.post("/login")
async def login(request: LoginRequest):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == request.email)
        )
        user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not bcrypt.checkpw(request.password.encode('utf-8'), user.hashed_password.encode('utf-8')):  
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = jwt.encode(
        {"user_id": user.id, "role": user.role},
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    return {"token": token}

async def require_admin(user_id: str = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(403, "User not found")
        if user.role != "admin":
            raise HTTPException(403, "Admin privileges required")
        return user_id