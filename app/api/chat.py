from fastapi import APIRouter
from pydantic import BaseModel
from app.core.rag import ask_question

router = APIRouter()


class ChatRequest(BaseModel): # si aspetta json format, quindi da postman fai il post su raw/json, e non da form-data (key/values) altrimenti manda un error
    user_id: str
    question: str

@router.post('/chat')
def chat_endpoint(payload:ChatRequest):
    response = ask_question(
        user_id=payload.user_id,
        question=payload.question
        )
    return response