from fastapi import Request, HTTPException, Depends
import jwt
from src.core.config import SECRET_KEY, ALGORITHM
from src.core.db import AsyncSessionLocal
from sqlalchemy import select
from src.schema.db_models import User



def get_current_user(request: Request):
    ## Print everything so we can see what's arriving
    # print("===== HEADERS RECEIVED =====")
    # for key, value in request.headers.items():
    #     print(f"{key}: {value}")
    # print("=============================")
    
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = auth_header.split()[1]
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload.get("user_id")

async def require_admin(user_id: str = Depends(get_current_user)):
    print(f"🔍 user_id from token: {user_id}")
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        print(f"👤 Retrieved user: {user}")
        if not user:
            raise HTTPException(403, "User not found")
        print(f"🔑 User role: {user.role}")
        if user.role != "admin":
            raise HTTPException(403, "Admin privileges required")
        return user_id