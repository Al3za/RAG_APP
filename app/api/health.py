from fastapi import APIRouter

router = APIRouter()

@router.get("/healt")
def healt_check():
    return {
        "status":"ok",
        "service":"rag-api" 
    }

# HEAD per i monitor (UptimeRobot)
@router.head("/healt")
def health_head(): ## per essere chiamato da uptime robot per evitare cold start
    #  (get puo non funzionar equando viene chiamato da robot)
    return {}