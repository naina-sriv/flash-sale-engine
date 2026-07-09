from pydantic import BaseModel, Field


class ItemRequest(BaseModel):
    id: str = Field(..., min_length=1)
    qty: int = Field(..., gt=0, le=1000000)
