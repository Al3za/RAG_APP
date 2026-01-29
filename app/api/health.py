from fastapi import APIRouter

router = APIRouter()

@router.get("/healt")
def healt_check():
    return {
        "status":"ok",
        "service":"rag-api"
    }