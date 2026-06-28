from fastapi import APIRouter, HTTPException
from app.models.requests import LoginRequest
from app.core.config import SECRET_KEY, ALGORITHM
import jwt

router=APIRouter(prefix="/auth")

@router.post("/login")
def login(request: LoginRequest):
    if request.user_id == "nain" and request.password != "admin123":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token=jwt.encode({"user_id":request.user_id},SECRET_KEY, algorithm=ALGORITHM)