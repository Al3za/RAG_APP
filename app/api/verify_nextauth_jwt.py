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
print('BACKEND_JWT_SECRET =', BACKEND_JWT_SECRET)

security = HTTPBearer()  # legge Authorization: Bearer <token>


# message: 401 Unauthorized se non passiamo nessun token dal frontend
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    token = credentials.credentials # il token generati da nextauth nel frontend
    # print('token here =', token)
    # print("TOKEN LEN:", len(token))
    # token = token + '1'
    # print("TOKEN LEN plus 1:", len(token))
    header = jwt.get_unverified_header(token)
    print(header)
    try:
        payload = jwt.decode( # check if jwt token is correct, else throws 401 error
            token,
            BACKEND_JWT_SECRET,
            algorithms=["HS256"],
            # options={"verify_exp": False}
        )
        # payload contiene: email, name, picture, sub, iat, exp
        print('middleware token payload verify =', payload)
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token") # se passiamo token invalido o expired 