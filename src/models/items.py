from pydantic import BaseModel
class ItemRequest(BaseModel): 
    id: str
    qty: int