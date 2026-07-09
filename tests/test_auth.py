import asyncio
import time

import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def sqlite_session_factory(monkeypatch):
    """
    Swap the real Postgres session with an in-memory SQLite one so these
    tests run without a live database, then patch it into every module
    that imported AsyncSessionLocal directly (auth.py, dependencies/auth.py).
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    from src.core import db as db_module

    async def _create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(db_module.Base.metadata.create_all)

    asyncio.run(_create_tables())

    import src.dependencies.auth as auth_deps
    import src.routes.auth as auth_routes

    monkeypatch.setattr(auth_deps, "AsyncSessionLocal", SessionLocal)
    monkeypatch.setattr(auth_routes, "AsyncSessionLocal", SessionLocal)
    return SessionLocal


def test_require_admin_rejects_non_admin(sqlite_session_factory):
    from src.dependencies.auth import require_admin
    from src.schema.db_models import User

    async def _do():
        async with sqlite_session_factory() as session:
            user = User(
                email="a@b.com", hashed_password="x", full_name="A", role="user"
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user_id=str(user.id))
        assert exc_info.value.status_code == 403

    asyncio.run(_do())


def test_require_admin_allows_admin(sqlite_session_factory):
    from src.dependencies.auth import require_admin
    from src.schema.db_models import User

    async def _do():
        async with sqlite_session_factory() as session:
            user = User(
                email="admin@b.com", hashed_password="x", full_name="A", role="admin"
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        result = await require_admin(user_id=str(user.id))
        assert result == str(user.id)

    asyncio.run(_do())


def test_expired_token_is_rejected():
    from src.core.config import ALGORITHM, SECRET_KEY
    from src.dependencies.auth import get_current_user

    expired_token = jwt.encode(
        {"user_id": 1, "exp": int(time.time()) - 10},  # expired 10s ago
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    class FakeRequest:
        headers = {"Authorization": f"Bearer {expired_token}"}

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(FakeRequest())
    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


def test_valid_token_is_accepted():
    from src.core.config import ALGORITHM, SECRET_KEY
    from src.dependencies.auth import get_current_user

    token = jwt.encode(
        {"user_id": 7, "exp": int(time.time()) + 300},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    class FakeRequest:
        headers = {"Authorization": f"Bearer {token}"}

    assert get_current_user(FakeRequest()) == 7
