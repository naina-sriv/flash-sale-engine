from pydantic import BaseModel


class SignupResponse(BaseModel):
    message: str
    user_id: int


class LoginResponse(BaseModel):
    token: str
    refresh_token: str
    expires_in_minutes: int


class RefreshResponse(BaseModel):
    access_token: str
    expires_in_minutes: int


class ForgotPasswordResponse(BaseModel):
    message: str


class ResetPasswordResponse(BaseModel):
    message: str


class BuyResponse(BaseModel):
    message: str


class ChallengeResponse(BaseModel):
    challenge_id: str
    question: str


class StockUpdateResponse(BaseModel):
    message: str


class AdminFlashResponse(BaseModel):
    message: str


class FlashListResponse(BaseModel):
    flash_items: list[str]


class HealthResponse(BaseModel):
    status: str
    redis: str
    postgres: str
    timestamp: float
