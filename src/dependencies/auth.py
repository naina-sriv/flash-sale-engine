import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select

from src.core.config import ALGORITHM, SECRET_KEY
from src.core.db import AsyncSessionLocal
from src.core.logger import logger
from src.schema.db_models import User


def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401, detail="Authorization header must be 'Bearer <token>'"
        )

    token = parts[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status_code=401, detail="Token has expired") from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e
    return payload.get("user_id")


async def require_admin(user_id: str = Depends(get_current_user)):
    logger.info(f"user_id from token: {user_id}")
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        logger.info(f"Retrieved user: {user}")
        if not user:
            raise HTTPException(403, "User not found")
        logger.info(f"User role: {user.role}")
        if user.role != "admin":
            raise HTTPException(403, "Admin privileges required")
        return user_id
