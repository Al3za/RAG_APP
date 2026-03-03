# app/core/cors.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv 

load_dotenv()

FRONTEND_URL = os.environ.get("FRONTEND_URL")

def setup_cors(app: FastAPI):

    origins = [
        "http://localhost:3000" # per sviluppo
    ]
    if FRONTEND_URL : # FRONTEND_URL e' nel .env di render ed e' usata in prod
        origins.append(FRONTEND_URL)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins, 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )