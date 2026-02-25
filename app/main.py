from fastapi import FastAPI, Depends 
from app.utils.verify_nextauth_jwt import get_current_user #jwt_nextauth_verify
from app.api.health import router as health_router # import the endpoint createn on this path
from app.api.jtw_test import router as jwt_router_test
from app.api.upload import router as upload_router # /upload_pdf
from app.api.chat import router as chat_router # dove facciamo le domande a chat riguardo i pdf
from app.core.config import settings
from app.core.coors import setup_cors
import os

app = FastAPI(title=settings.APP_NAME) # "RAG PDF API"

setup_cors(app) # COORS centralizzato

app.include_router(health_router)
app.include_router(jwt_router_test, dependencies=[Depends(get_current_user)]) # verify this route and get the email
app.include_router(upload_router, dependencies=[Depends(get_current_user)])
app.include_router(chat_router, dependencies=[Depends(get_current_user)]) 

@app.get("/")
def root():  
    return {"message": "RAG API running (autodeploy working)"}


# Avvio locale

# Da root del progetto:
# uvicorn app.main:app --reload

# Apri:

# http://localhost:8000

# http://localhost:8000/health


# da render:

# https://rag-app-2s6e.onrender.com
# https://rag-app-2s6e.onrender.com/healt

# test autodeploy render

