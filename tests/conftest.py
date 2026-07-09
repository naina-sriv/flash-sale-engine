import os
import sys

import fakeredis
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def fake_redis():
    """A fresh in-memory Redis stand-in per test. If a real Redis is running on localhost, use it instead, cleaning it up before/after."""
    import os

    import redis

    use_real = os.getenv("USE_REAL_REDIS", "false").lower() == "true"
    if use_real:
        client = redis.Redis(host="localhost", port=6379, decode_responses=True)
        try:
            client.ping()
            client.flushdb()
            yield client
            client.flushdb()
            return
        except Exception as e:
            print(f"Failed to connect to real Redis, falling back to fakeredis: {e}")
            pass
    yield fakeredis.FakeStrictRedis(decode_responses=True)


@pytest.fixture
def buy_module(fake_redis, monkeypatch):
    """
    Import src.routes.buy with its module-level redis_client swapped for
    fakeredis, and its DB-writing background task stubbed out so these
    tests exercise only the Redis-side correctness guarantees
    (no-oversell, duplicate-purchase lock) without needing a real Postgres.
    """
    import src.routes.buy as buy

    monkeypatch.setattr(buy, "redis_client", fake_redis)

    async def fake_process_payment(user_id, item_ids):
        # DB persistence is covered separately; here we isolate the
        # Redis stock/lease logic that this test suite targets.
        return None

    monkeypatch.setattr(buy, "process_payment", fake_process_payment)
    return buy
