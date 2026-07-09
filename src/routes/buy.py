import asyncio
import random
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.core.db import AsyncSessionLocal
from src.core.logger import logger
from src.core.redis_client import redis_client
from src.dependencies.auth import get_current_user
from src.dependencies.rate_limiter import buy_rate_limiter
from src.models.requests import BuyRequest
from src.models.responses import BuyResponse, ChallengeResponse
from src.schema.db_models import Order, Product


async def process_payment(user_id: str, item_ids: list):
    logger.info("Background task started...")
    await asyncio.sleep(3)
    logger.info(f"Payment successful for user {user_id} for items {item_ids}")

    flash_purchased = False
    try:
        async with AsyncSessionLocal() as session:
            for item_id in item_ids:
                prod_result = await session.execute(
                    select(Product).where(Product.id == int(item_id))
                )
                product = prod_result.scalar_one_or_none()

                is_flash = redis_client.sismember("flash_items", str(item_id))
                if not product:
                    logger.error(f"Product {item_id} not found in DB!")
                    price = 10.0
                else:
                    if is_flash and product.flash_price is not None:
                        price = product.flash_price
                    else:
                        price = product.price

                flash_sale_date = None
                if is_flash:
                    flash_sale_date = datetime.now(UTC).date()
                    flash_purchased = True

                new_order = Order(
                    user_id=int(user_id),
                    product_id=int(item_id),
                    quantity=1,
                    price_at_purchase=price,
                    status="paid",
                    flash_sale_date=flash_sale_date,
                )
                session.add(new_order)
            await session.commit()
            logger.info(f"Order(s) saved for user {user_id}")
    except IntegrityError as ie:
        logger.error(f"DB integrity error during order save for user {user_id}: {ie}")
        logger.info(f"Rolling back Redis stock decrements for user {user_id}...")
        for item_id in item_ids:
            redis_client.incr(f"stock:{item_id}")
        redis_client.delete(f"lease:{user_id}")
        if flash_purchased:
            redis_client.delete(f"purchased_flash:{user_id}")
    except Exception as e:
        logger.error(
            f"Unexpected error during order persistence for user {user_id}: {e}"
        )
        logger.info(f"Rolling back Redis stock decrements for user {user_id}...")
        for item_id in item_ids:
            redis_client.incr(f"stock:{item_id}")
        redis_client.delete(f"lease:{user_id}")
        if flash_purchased:
            redis_client.delete(f"purchased_flash:{user_id}")


router = APIRouter(prefix="/buy")


@router.get("/challenge", response_model=ChallengeResponse)
async def get_challenge(user_id: str = Depends(get_current_user)):
    num1 = random.randint(1, 20)
    num2 = random.randint(1, 20)
    op = random.choice(["+", "-", "*"])
    question = f"What is {num1} {op} {num2}?"

    if op == "+":
        ans = num1 + num2
    elif op == "-":
        ans = num1 - num2
    else:
        ans = num1 * num2

    redis_client.setex(f"challenge:{user_id}", 60, ans)
    return ChallengeResponse(challenge_id=user_id, question=question)


@router.post("/", response_model=BuyResponse)
async def click_buy(req: BuyRequest, user_id: str = Depends(buy_rate_limiter)):
    # 0. Check block
    if redis_client.exists(f"blocked_user:{user_id}"):
        raise HTTPException(
            status_code=403,
            detail="User account temporarily blocked due to repeated failed attempts.",
        )

    # Helper function to handle failed buy attempts
    def record_failed_attempt(user_id: str):
        failed_count = redis_client.incr(f"failed_buy_attempts:{user_id}")
        if failed_count == 1:
            redis_client.expire(f"failed_buy_attempts:{user_id}", 60)
        if failed_count >= 5:
            logger.warning(
                f"[ALERT] Abuse: user {user_id} exceeded failure "
                f"limit ({failed_count} fails)."
            )
            redis_client.setex(f"blocked_user:{user_id}", 300, "blocked")

    # 1. Challenge verification
    saved_challenge = redis_client.get(f"challenge:{user_id}")
    if not saved_challenge:
        record_failed_attempt(user_id)
        raise HTTPException(
            status_code=400,
            detail="Challenge expired or not found. Call /buy/challenge first.",
        )

    try:
        if int(saved_challenge) != req.challenge_answer:
            record_failed_attempt(user_id)
            raise HTTPException(status_code=400, detail="Incorrect challenge answer.")
    except (ValueError, TypeError) as e:
        record_failed_attempt(user_id)
        raise HTTPException(
            status_code=400, detail="Invalid challenge answer format."
        ) from e

    # Remove challenge once verified to prevent reuse
    redis_client.delete(f"challenge:{user_id}")

    lease_key = f"lease:{user_id}"
    if redis_client.exists(lease_key):
        record_failed_attempt(user_id)
        return BuyResponse(message="some item is already reserved for you.")
    if req.item_id == []:
        record_failed_attempt(user_id)
        return BuyResponse(message="no item in cart")
    if len(req.item_id) != len(set(req.item_id)):
        record_failed_attempt(user_id)
        return BuyResponse(message="duplicates not allowed")
    count = 0
    for i in req.item_id:
        if redis_client.sismember("flash_items", i):
            if redis_client.exists(f"purchased_flash:{user_id}"):
                record_failed_attempt(user_id)
                return BuyResponse(message="only one flash order per customer")
            count += 1
    if count > 1:
        record_failed_attempt(user_id)
        return BuyResponse(message="You can buy only one flash sale item per order")
    reserved_items = []
    for i in req.item_id:
        new_val = redis_client.decr(f"stock:{i}")
        if new_val < 0:
            redis_client.incr(
                f"stock:{i}"
            )  # undo this item's own decrement, not just prior ones
            for j in reserved_items:
                redis_client.incr(f"stock:{j}")
            redis_client.delete(f"lease:{user_id}")
            record_failed_attempt(user_id)
            return BuyResponse(message=f"out of stock item {i}")
        else:
            reserved_items.append(i)
    redis_client.setex(lease_key, 10, "active")
    if count == 1:
        redis_client.setex(f"purchased_flash:{user_id}", 89400, "active")

    # Reset failed attempts on success
    redis_client.delete(f"failed_buy_attempts:{user_id}")

    asyncio.create_task(process_payment(user_id, req.item_id))
    return BuyResponse(message="reserved")


class StressBuyRequest(BaseModel):
    user_id: str
    item_id: str


@router.post("/stress")
async def stress_buy(req: StressBuyRequest):
    user_id = req.user_id
    item_id = req.item_id

    lease_key = f"lease:{user_id}"
    if redis_client.exists(lease_key):
        return {"message": "already reserved"}

    new_val = redis_client.decr(f"stock:{item_id}")
    if new_val < 0:
        redis_client.incr(f"stock:{item_id}")
        return {"message": "out of stock"}

    redis_client.set(lease_key, "active", ex=10)
    return {"message": "reserved"}
