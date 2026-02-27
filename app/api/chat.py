from fastapi import APIRouter, Depends
# from app.utils.hashed_email import email_to_namespace
from app.utils.auth import get_user_namespace
from pydantic import BaseModel
from app.core.rag import ask_question
from app.utils.rate_limiter import rate_limit

router = APIRouter()

# mai fidarsi dal body frontend. ricava sempre user_id, role, email dal jwt token del backend
class ChatRequest(BaseModel): # si aspetta json format, quindi da postman fai il post su raw/json, e non da form-data (key/values) altrimenti manda un error
    question: str

@router.post('/chat')
def chat_endpoint(payload: ChatRequest,
                  namespace: str = Depends(get_user_namespace)):  # payload:ChatRequest
   
    # print('namespace chat here =', namespace)
    # print('payload.question =', payload.question)
    rate_limit(namespace) # docker start my-redis
    response = ask_question( # la function in rag.py che ci connette con pinecone e fa' il retriver
        user_namespace= namespace, #payload.hashed_user_mail, 
        question=payload.question 
        )
    return response