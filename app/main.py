from fastapi import FastAPI
from app.api.health import router as health_router # import the endpoint createn on this path
from app.api.upload import router as upload_router # /upload_pdf
from app.core.config import settings

app = FastAPI(title=settings.APP_NAME) # "RAG PDF API"

app.include_router(health_router) # "/healt", import api endpoint defined in app.api.health (scalable)
app.include_router(upload_router)

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

