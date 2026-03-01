from fastapi import APIRouter
from app.utils.redis_client import redis_client

router = APIRouter()

@router.get("/redis_test")
def redis_test():
    redis_client.set("render_test", "connected", ex=60) 
    return  {"value": redis_client.get("render_test")}

# vai su https://rag-app-2s6e.onrender.com/redis_test dopa aver deployato su renderper vedere se redis
#  funziona anche su render e' non solo in locale
# se vedi come return "{"value":"connected"}", 🎉 Redis è collegato correttamente in produzione."



