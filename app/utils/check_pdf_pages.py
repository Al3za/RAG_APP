from PyPDF2 import PdfReader
from fastapi import UploadFile, HTTPException

MAX_PAGES = 50

async def check_pdf_pages(file: UploadFile):
    reader = PdfReader(file.file)
    total_pages = len(reader.pages)

    print('total_pages here =', total_pages)
    if total_pages > MAX_PAGES: ## Qui blocchiamo il backend(400) e inviamo il mess sotto al frontend
        raise HTTPException(
            status_code=400,
            detail=f"PDF exceeds {MAX_PAGES} pages limit. Please upload a smaller pdf" # l'error che finisce nel frontend
        )

    # IMPORTANTISSIMO, PdfReader consuma lo stream, Se non lo resetti, 
    # l’ingest successivo leggerà file vuoto
    file.file.seek(0)

    return total_pages