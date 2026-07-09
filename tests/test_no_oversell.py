"""
This is the test that actually proves the project's core claim:
under concurrent purchase requests for limited stock, Redis's atomic
DECR prevents overselling — no customer gets a "reserved" response
for stock that doesn't exist.

Uses real OS threads (not asyncio.gather) because click_buy() has no
`await` between its stock check and its decrement — inside a single
event loop those calls never actually interleave, so asyncio.gather
alone would "pass" without testing anything. Threads give genuine
parallelism at the point where the race would matter in production
(multiple Uvicorn workers hitting the same Redis instance).
"""
import asyncio
import concurrent.futures

from src.models.requests import BuyRequest


def run_one_purchase(buy_module, user_id: str, item_id: str):
    async def _do():
        req = BuyRequest(user_id=user_id, item_id=[item_id])
        return await buy_module.click_buy(req, user_id=user_id)
    return asyncio.run(_do())


def test_no_oversell_under_concurrent_requests(buy_module, fake_redis):
    STARTING_STOCK = 5
    NUM_CONCURRENT_BUYERS = 30
    ITEM_ID = "1"

    fake_redis.set(f"stock:{ITEM_ID}", STARTING_STOCK)

    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_CONCURRENT_BUYERS) as pool:
        futures = [
            pool.submit(run_one_purchase, buy_module, str(i), ITEM_ID)
            for i in range(NUM_CONCURRENT_BUYERS)
        ]
        results = [f.result() for f in futures]

    reserved = [r for r in results if r.get("message") == "reserved"]
    out_of_stock = [r for r in results if "out of stock" in r.get("message", "")]

    # Exactly as many purchases should succeed as there was stock —
    # not more (overselling) and not fewer (over-rejecting).
    assert len(reserved) == STARTING_STOCK, (
        f"Expected exactly {STARTING_STOCK} successful reservations, "
        f"got {len(reserved)}. Results: {results}"
    )
    assert len(out_of_stock) == NUM_CONCURRENT_BUYERS - STARTING_STOCK

    # Stock must never go negative — that's the actual failure mode
    # ("overselling") this whole project exists to prevent.
    final_stock = int(fake_redis.get(f"stock:{ITEM_ID}"))
    assert final_stock == 0, f"Stock went to {final_stock}, expected exactly 0 (never negative)"


def test_duplicate_purchase_blocked_by_lease(buy_module, fake_redis):
    """A user with an active lease can't submit a second purchase
    while the first is still being 'processed'."""
    fake_redis.set("stock:1", 10)
    fake_redis.set("stock:2", 10)

    async def _do():
        req1 = BuyRequest(user_id="1", item_id=["1"])
        first = await buy_module.click_buy(req1, user_id="1")

        req2 = BuyRequest(user_id="1", item_id=["2"])
        second = await buy_module.click_buy(req2, user_id="1")
        return first, second

    first, second = asyncio.run(_do())

    assert first["message"] == "reserved"
    assert "already reserved" in second["message"]
    # Stock for item 2 must be untouched since the second request was blocked
    assert int(fake_redis.get("stock:2")) == 10


def test_rollback_restores_stock_on_partial_failure(buy_module, fake_redis):
    """If a multi-item order fails partway through (one item out of
    stock), previously decremented stock in that same order is restored."""
    fake_redis.set("stock:1", 1)   # only 1 left
    fake_redis.set("stock:2", 0)   # already sold out

    async def _do():
        req = BuyRequest(user_id="42", item_id=["1", "2"])
        return await buy_module.click_buy(req, user_id="42")

    result = asyncio.run(_do())

    assert "out of stock" in result["message"]
    # item 1 was decremented then rolled back — must be back to 1, not 0
    assert int(fake_redis.get("stock:1")) == 1
