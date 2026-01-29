from fastapi import  APIRouter, UploadFile, File, Form
import boto3
import os
from uuid import uuid4

router = APIRouter()

s3 = boto3.client(
     "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
) # connessione con il nostro aws "user", dove abbiamo allegato permessi e policy di read/update/delete verso il bucket s3, quello che ospitera i pdf dei clienti che useranno l'app

BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

@router.post("/upload_pdf")
async def upload_pdf(user_id: str = Form(...), file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        return {"error": "Only PDF files are allowed for this demo"}
    
    file_key = f"{user_id}/{uuid4()}_{file.filename}"
    
    s3.upload_fileobj(file.file, BUCKET_NAME, file_key)
    
    return {"message": "PDF uploaded successfully", "file_key": file_key}
