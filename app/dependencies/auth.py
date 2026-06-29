from fastapi import Request, HTTPException
import jwt
from app.core.config import SECRET_KEY, ALGORITHM

def get_current_user(request: Request):
    ## Print everything so we can see what's arriving
    # print("===== HEADERS RECEIVED =====")
    # for key, value in request.headers.items():
    #     print(f"{key}: {value}")
    # print("=============================")
    
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = auth_header.split()[1]
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload.get("user_id")