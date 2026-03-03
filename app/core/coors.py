# app/core/cors.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os


def setup_cors(app: FastAPI):

    FRONTEND_URL = os.environ.get(
        'NEXTAUTH_URL', # url del frontend su render salvata su render backend .env
        "http://localhost:3000" # fallback per sviluppo
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[FRONTEND_URL], 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )