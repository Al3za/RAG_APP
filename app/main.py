from fastapi import FastAPI
from app.api.health import router as health_router # import the endpoint createn on this path
from app.core.config import settings

app = FastAPI(title=settings.APP_NAME) # "RAG PDF API"

app.include_router(health_router) # "/healt", impo

@app.get("/")
def root():
    return {"message": "RAG API running"}


# Avvio locale

# Da root del progetto:
# uvicorn app.main:app --reload

# Apri:

# http://localhost:8000

# http://localhost:8000/health