from fastapi import APIRouter

router = APIRouter()
# HEAD per i monitor (UptimeRobot)
@router.head("/healt_head")
def health_head(): ## per essere chiamato da uptime robot per evitare cold start
    #  (get puo non funzionar equando viene chiamato da robot)
    print('hit here')
    return {}