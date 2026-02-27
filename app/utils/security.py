# (verifica JWT)

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
# import json
from typing import Dict
import os
from dotenv import load_dotenv 
load_dotenv()

# Il secret deve essere lo stesso usato in NextAuth
BACKEND_JWT_SECRET = os.environ.get("BACKEND_JWT_SECRET") # Same secret key as the frontend
# print('BACKEND_JWT_SECRET =', BACKEND_JWT_SECRET)

security = HTTPBearer()  # legge Authorization: Bearer <token>


# message: 401 Unauthorized se non passiamo nessun token dal frontend
def verify_jwt_token(token: str) -> dict: # Jwt token verify
    
    # print('token here 1', token)
    try:
        payload = jwt.decode( # check if jwt token is correct, else throws 401 error
            token,
            BACKEND_JWT_SECRET,
            algorithms=["HS256"],
        )
        
        # payload contiene: email, name, picture, sub, iat, exp
        # print('middleware token payload verify =', payload)
        return payload
    except JWTError:
        raise HTTPException(status_code=401, 
                            detail="Invalid or expired token") # se passiamo token invalido o expired 