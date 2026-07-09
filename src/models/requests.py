from pydantic import BaseModel, EmailStr, Field


class BuyRequest(BaseModel):
    user_id: str
    item_id: list[str]
    challenge_answer: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=1)
