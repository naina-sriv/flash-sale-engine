from fastapi import APIRouter

router=APIRouter(prefix="/admin")

@router.post("/add_item")
def add_item():
    
    