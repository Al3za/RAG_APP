from fastapi import APIRouter, Depends
# from app.utils.hashed_email import email_to_namespace
from app.utils.auth import get_user_namespace
from app.utils.rate_limiter import get_ingest_status, rate_limit

router = APIRouter()

# Lo status che dice allo user sul frontend quando poter fare domande all'LLM sul pdf
# Cosi lato next frontend, cambiamo pagina su quando il pdf e stato "ingested" e carricato correttamente su s3 e pinecon
# Evitando il rischio che il client facesse una domanda sul prima ancora che il pdf fosse caricato
@router.get("/ingestion_status")
def document_status(namespace: str = Depends(get_user_namespace)):
    print('get_ingest_status here')
    status = get_ingest_status(namespace) #redis_client.get(f"doc_status:{namespace}") 
    print('get_ingest_status here =', status)
    return {"status": status or "not_found"}