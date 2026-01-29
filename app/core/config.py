from dotenv import load_dotenv # terminal: Get-Command python. output venv\Scripts\python.exe. cosi vscode e' in sink con il terminal dove hai aperto il venv, e trova i packetti installati
import os

load_dotenv()

class Settings:
    APP_NAME = "RAG PDF API"
    ENV = os.getenv("ENV", "dev")

settings = Settings()
