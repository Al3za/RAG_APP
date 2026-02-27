from fastapi import  Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# from jose import jwt, JWTError
# from typing import Dict
import os
from dotenv import load_dotenv 
from app.utils.security import verify_jwt_token # verify jwt first
from app.utils.hashed_email import email_to_namespace
load_dotenv()

# Il secret deve essere lo stesso usato in NextAuth
BACKEND_JWT_SECRET = os.environ.get("BACKEND_JWT_SECRET") # Same secret key as the frontend
# print('BACKEND_JWT_SECRET =', BACKEND_JWT_SECRET)

security = HTTPBearer()  # legge Authorization: Bearer <token>


def get_current_payload( # get the verified payload 
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    token = credentials.credentials
    # print('chek token =', token)
    return verify_jwt_token(token)

# message: 401 Unauthorized se non passiamo nessun token dal frontend

def get_user_namespace( # Hash the verified user_email from ricavto dall verified payload
    payload: dict = Depends(get_current_payload)
) -> str:
    email = payload.get("email") 
    # print('get_user_namespace email here', email)
    return email_to_namespace(email) # return the hashed email

# def get_current_user(
#     credentials: HTTPAuthorizationCredentials = Depends(security)
# ) -> Dict:
#     token = credentials.credentials # il custom token generato nel frontend 
#     # header = jwt.get_unverified_header(token)
#     # print(header)
#     try:
#         payload = jwt.decode( # check if jwt token is correct, else throws 401 error
#             token,
#             BACKEND_JWT_SECRET,
#             algorithms=["HS256"],
#         )
        
#         # payload contiene: email, name, picture, sub, iat, exp
#         print('middleware token payload verify =', payload)
#         return payload
#     except JWTError:
#         raise HTTPException(status_code=401, detail="Invalid or expired token") # se passiamo token invalido o expired 