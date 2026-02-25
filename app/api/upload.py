from fastapi import  APIRouter, UploadFile, File, Form, BackgroundTasks, Depends
from app.utils.jwt_email import email_to_namespace
from app.utils.verify_nextauth_jwt import get_current_user
from app.core.ingest import ingest_pdf
import tempfile
import boto3
import os
from uuid import uuid4
from dotenv import load_dotenv

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
async def upload_pdf(user_email: dict = Depends(get_current_user), # otteniamo l'email dal token inviato dal frontend. Non inviamo l'email direttamente in plain text
                     file: UploadFile = File(...), 
                     background_tasks: BackgroundTasks=None): # Dopo l’upload del pdf in s3, avvii l’ingest dei chunks embeddings in background, Scarichando il PDF da S3 (temporaneo) e passandolo alla funzione ingest_pdf(file_path, user_id) 
    
    if not file.filename.endswith(".pdf"):
        return {"error": "Only PDF files are allowed for this demo"}
    
    # hash the jwt user email before storing it in s3 and pinecone namespaces 
    email = user_email['email']
    hashed_user_email = email_to_namespace(email) # working
    print('email and hased email =', email, hashed_user_email )
    # akecakabro@gmail.com and 7ac49cad74737bbd98ca7d3d74a45b7b8f852a91d9022a21221ee14a8cd27712

    file_key = f"{hashed_user_email}/{uuid4()}_{file.filename}"
    
    # 1️⃣ Upload pdf su S3
    s3.upload_fileobj(file.file, BUCKET_NAME, file_key)

  
    # questo blocco codice serve a:
    # salvare il pdf che abbiamo scaricato da s3 in locale (es: C:\Users\ale\AppData\Local\Temp\tmpx8f3s9.pdf) fino a quando facciamo 
    # chunk,emb, e pinecone storage, e poi chiudiamo il service e ripuliamo il file locale(questo in ingest.py file in "finally") 
    # dove abbiamo salvato questo file.
    
      # 2️⃣ Scarica da S3 in file TEMP (persistente). Il file pdf deve esistere per tutta la durata del background task, per questo usiamo delete=false
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) # TEMP (persistente). NamedTemporaryFile crea un file fisico sul disco, es: C:\Users\ale\AppData\Local\Temp\tmpx8f3s9.pdf
    s3.download_fileobj(BUCKET_NAME, file_key, tmp) # download il file appena caricato su s3
    tmp.close()  # IMPORTANTISSIMO. Flush dei buffer del serviziod download del file. PyPDFLoader fallirebbe se il file restasse aperto

    # 3️⃣ Ingest in background il pdf file appena downloaded da s3
    background_tasks.add_task(ingest_pdf, tmp.name, hashed_user_email) # avvia ingest operation in background sul file pdf che e' stato appena caricato su s3.
    # (funzione asyncrona, riceviamo subito il return, ma il file viene processato in background)

    return {"message": "PDF uploaded successfully and ingestion started in background", 
            "file_key": file_key}



# # # 🔹 descrizione di cosa avviene in questo file quando uno user posta il pdf che vuole caricare:

# # # PDF dello user caricati su S3

# # # Scarichi PDF da s3 nella tua app Python

# salvi il pdf scaricato da s3 in un file temporaneo nel mio pc. dopodiche invochi la funzione ingest_pdf che passa come parametro il file pdf
# scaricato da s3(che e' quello appena carricato dallo user), e in questa funzione il file pdf subisce:

# # # Chunking con LangChain (RecursiveCharacterTextSplitter)

# # # Generi embeddings con OpenAI (text-embedding-3-small)

# # # Crei index Pinecone da Python se non esiste ancora

# # # Inserisci embeddings nell’index (con namespace = user_id)