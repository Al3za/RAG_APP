from fastapi import  APIRouter, UploadFile, File, BackgroundTasks, Depends
from app.utils.check_pdf_pages import check_pdf_pages
from app.utils.auth import get_user_namespace
from app.core.ingest import ingest_pdf
from app.utils.rate_limiter import rate_limit
import tempfile
import boto3
import os
from uuid import uuid4
from dotenv import load_dotenv
from app.utils.rate_limiter import ingest_status

load_dotenv()

router = APIRouter()

s3 = boto3.client(
     "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
) # connessione con il nostro aws "user", dove abbiamo allegato permessi e policy di read/update/delete verso il bucket s3, quello che ospitera i pdf dei clienti che useranno l'app

BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
# print('BUCKET_NAME checkd', BUCKET_NAME)


@router.post("/upload_pdf")
async def upload_pdf(namespace: str = Depends(get_user_namespace), # otteniamo l'email dal token inviato dal frontend. Non inviamo l'email direttamente in plain text
                     file: UploadFile = File(...), 
                     background_tasks: BackgroundTasks=None): # Dopo l’upload del pdf in s3, 
                    #  avvii l’ingest dei chunks embeddings in background, Scarichando il PDF da S3 
                    # (temporaneo) e passandolo alla funzione ingest_pdf(file_path, user_id) 
    
    if not file.filename.endswith(".pdf"):
        return {"error": "Only PDF files are allowed for this demo"}

    # RATE LIMIT HERE
    
    rate_limit(namespace) # docker start my-redis in local 

    print('rate limit')
    ## CHECK TOTAL PDF PAGE (NOT BIGGER THAT 50 PAGES ALLOWED). Se non > 50, salva su s3, e procedi con ingest
    await check_pdf_pages(file) # se un pdf caricato dal frontend e' > 50 pages ritorna error(si blocca qui e manda error detail al frontend) 
    # altrimenti continua con s3 storage e ingest 
    

    
   # namespace is hashed
    # file_key = f"{namespace}/{uuid4()}_{file.filename}" # working
    file_key = f"{namespace}/latest.pdf" # sovrascrive il pdf caricato prima

    
    # 1️⃣ Upload pdf su S3
    s3.upload_fileobj(file.file, BUCKET_NAME, file_key)

    
      # 2️⃣ Scarica da S3 in file TEMP (persistente). Il file pdf deve esistere per tutta la durata del background task, per questo usiamo delete=false
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) # TEMP (persistente). NamedTemporaryFile crea un file fisico sul disco, es: C:\Users\ale\AppData\Local\Temp\tmpx8f3s9.pdf
    s3.download_fileobj(BUCKET_NAME, file_key, tmp) # download il file appena caricato su s3
    tmp.close()  # Flush dei buffer del serviziod download del file (IMPORTANTISSIMO).

    print('ingest_status')
    ingest_status(namespace,'processing') # gli argomenti da passare a redis
    print('ingest_status upload', )
   
    # 3️⃣ Ingest in background il pdf file appena downloaded da s3
    background_tasks.add_task(ingest_pdf, tmp.name, namespace) # avvia ingest operation in background sul file pdf che e' stato appena caricato su s3.
    # (funzione asyncrona, riceviamo subito il return, ma il file viene processato in background)

    return {"message": "PDF uploaded successfully and ingestion started in background", 
            "file_key": file_key}


# Ulteriori dettagli sul file upload_descrizione.py  