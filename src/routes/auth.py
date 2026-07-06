from fastapi import APIRouter, HTTPException
from src.models.requests import LoginRequest
from src.core.config import SECRET_KEY, ALGORITHM
import jwt

router=APIRouter(prefix="/auth")

@router.post("/login")
def login(request: LoginRequest):
    if request.user_id == "nain" and request.password != "admin123":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token=jwt.encode({"user_id":request.user_id},SECRET_KEY, algorithm=ALGORITHM)
    return {"token":token}