from fastapi import APIRouter, Depends
from app.utils.auth import get_user_namespace
from app.utils.rate_limiter import rate_limit

router = APIRouter()

@router.get("/jwt_test")
def jwt_testes(namespace: str = Depends(get_user_namespace)): 
    rate_limit(namespace) # docker start my-redis in local
    print('namespace here jwt test =',namespace)
    
    return {
        "message": namespace
    }
   