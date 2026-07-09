from fastapi import APIRouter, Depends

from src.core.redis_client import redis_client
from src.dependencies.auth import require_admin
from src.models.items import ItemRequest
from src.models.responses import StockUpdateResponse

router = APIRouter(prefix="/stock")


@router.get("/", response_model=dict[str, int])
def get_stock():
    list_items = redis_client.keys("stock:*")
    result = {}
    for item in list_items:
        result[item] = int(redis_client.get(item) or 0)
    return result


@router.post("/set", response_model=StockUpdateResponse)
async def set_stock(item: ItemRequest, _=Depends(require_admin)):
    redis_client.set(f"stock:{item.id}", item.qty)
    return StockUpdateResponse(message="stock updated")
