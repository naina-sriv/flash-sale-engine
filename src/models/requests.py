from pydantic import BaseModel

class BuyRequest(BaseModel):
    user_id: str
    item_id: list[str]

class LoginRequest(BaseModel):
    email: str
    password: str