from fastapi import APIRouter, Depends
from app.utils.jwt_email import email_to_namespace
from app.utils.verify_nextauth_jwt import get_current_user
from pydantic import BaseModel
from app.core.rag import ask_question

router = APIRouter()


class ChatRequest(BaseModel): # si aspetta json format, quindi da postman fai il post su raw/json, e non da form-data (key/values) altrimenti manda un error
    hashed_user_mail: str
    question: str

@router.post('/chat')
def chat_endpoint(payload:ChatRequest): 
    user_email = get_current_user()
    email = user_email['email']
    hashed_user_email = email_to_namespace(email)
    response = ask_question( # la function in rag.py che ci connette con pinecone e fa' il retriver
        user_id= hashed_user_email, #payload.hashed_user_mail,
        question=payload.question
        )
    return response