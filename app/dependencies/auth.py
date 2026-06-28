import jwt
from fastapi import HTTPException, Header
from app.core.config import SECRET_KEY, ALGORITHM

def get_current_user(authorization:str=Header(...)):
    try:
        token=authorization.split()[1]
        payload=jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("user_id")
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
    
