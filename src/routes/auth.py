import asyncio
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from src.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
)
from src.core.db import AsyncSessionLocal
from src.core.logger import logger
from src.core.redis_client import redis_client
from src.dependencies.rate_limiter import login_rate_limiter
from src.models.requests import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    SignupRequest,
)
from src.models.responses import (
    ForgotPasswordResponse,
    LoginResponse,
    RefreshResponse,
    ResetPasswordResponse,
    SignupResponse,
)
from src.schema.db_models import User

router = APIRouter(prefix="/auth")


def create_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.now(UTC) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/signup", response_model=SignupResponse, status_code=201)
async def signup(request: SignupRequest):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == request.email))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

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

    token_data = {"user_id": str(user.id), "role": user.role}
    access_token = create_token(
        token_data, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_token(
        {**token_data, "type": "refresh"}, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )

    logger.info(f"User logged in: id={user.id}")
    return LoginResponse(
        token=access_token,
        refresh_token=refresh_token,
        expires_in_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(request: RefreshRequest):
    try:
        payload = jwt.decode(request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id = payload.get("user_id")
        role = payload.get("role")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        new_access_token = create_token(
            {"user_id": user_id, "role": role},
            timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        return RefreshResponse(
            access_token=new_access_token,
            expires_in_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
        )
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status_code=401, detail="Refresh token has expired") from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from e


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(request: ForgotPasswordRequest):
    import secrets

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == request.email))
        user = result.scalar_one_or_none()

    if user:
        reset_token = secrets.token_urlsafe(32)
        # Store token in Redis with 15 minute expiration
        redis_client.setex(f"reset_token:{reset_token}", 900, str(user.id))
        logger.info(f"Reset token generated for user {user.id}: {reset_token}")
        # In a real app, send email here!

    # Always return success to prevent email enumeration
    return ForgotPasswordResponse(
        message="If that email is registered, a password reset link has been sent."
    )


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(request: ResetPasswordRequest):
    user_id_str = redis_client.get(f"reset_token:{request.reset_token}")
    if not user_id_str:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    def hash_password(pw: str) -> str:
        return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    hashed_pw = await asyncio.to_thread(hash_password, request.new_password)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == int(user_id_str)))
        user = result.scalar_one_or_none()
        if user:
            user.hashed_password = hashed_pw
            session.add(user)
            await session.commit()

    redis_client.delete(f"reset_token:{request.reset_token}")
    return ResetPasswordResponse(message="Password successfully reset")
