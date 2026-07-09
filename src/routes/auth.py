import asyncio
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from src.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from src.core.db import AsyncSessionLocal
from src.core.logger import logger
from src.dependencies.rate_limiter import login_rate_limiter
from src.models.requests import LoginRequest, SignupRequest
from src.models.responses import LoginResponse, SignupResponse
from src.schema.db_models import User

router = APIRouter(prefix="/auth")


@router.post("/signup", response_model=SignupResponse, status_code=201)
async def signup(request: SignupRequest):
    async with AsyncSessionLocal() as session:
        # Check if email exists
        result = await session.execute(select(User).where(User.email == request.email))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Hash password (offload CPU-bound task to thread)
        def hash_password(pw: str) -> str:
            return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        hashed_pw = await asyncio.to_thread(hash_password, request.password)

        new_user = User(
            email=request.email,
            hashed_password=hashed_pw,
            full_name=request.full_name,
            role="user",
        )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)

        logger.info(f"New user registered: id={new_user.id}, email={new_user.email}")
        return SignupResponse(
            message="User registered successfully", user_id=new_user.id
        )


@router.post(
    "/login", response_model=LoginResponse, dependencies=[Depends(login_rate_limiter)]
)
async def login(request: LoginRequest):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == request.email))
        user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    def verify_password(plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

    is_valid = await asyncio.to_thread(
        verify_password, request.password, user.hashed_password
    )
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode(
        {"user_id": str(user.id), "role": user.role, "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    logger.info(f"User logged in: id={user.id}")
    return LoginResponse(token=token, expires_in_minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
