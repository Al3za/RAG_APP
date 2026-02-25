from fastapi import APIRouter, Depends
from app.utils.verify_nextauth_jwt import get_current_user

router = APIRouter()

@router.get("/jwt_test")
def jwt_testes(user: dict = Depends(get_current_user)): 
    print("email from backend =", user["email"])
    return {
        "message": user["email"]
    }
    # return {
    #     "status":"ok",
    #     "service":"jwt_test"
    # }