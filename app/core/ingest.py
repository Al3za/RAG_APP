import os
import re
from dotenv import load_dotenv 

from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore, Pinecone
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings # il modello AI per creare embeddings semantici
from pinecone import Pinecone, ServerlessSpec # SDK Pinecone
from app.core.cosine_similarity_fun import semantic_chunk_paragraphs
from app.core.merge_small_chunk import merge_small_chunks
from app.core.page_overlap  import build_page_windows

# NEL FILE ingest_desc.py VIENE SPIEGATO DETTAGLIATAMENTE COSA AVVIENE IN QUESTO FILE RIGA PER RIGA

load_dotenv()

# # Inizializza Pinecone SDK

# 1️⃣ Crea istanza Pinecone SDK
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# 2️⃣ Index name dal .env
index_name = os.getenv("PINECONE_INDEX_NAME") # gia creato sotto, basta crearlo 1 volta per questo e' commentato


embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")

def ingest_pdf(file_path: str, user_id: str):
    
    try:
        print('user_id = ', user_id)
    # 1️⃣ Carica PDF
        loader = PyPDFLoader(file_path) # PyPDFLoader si assicura che  che ogni Document(docs sotto) è UNA pagina del pdf la quale poi viene  applicato il chunking
        docs = loader.load() 
          #   /-------------/
       # 2️⃣ Chunking
        splitter = RecursiveCharacterTextSplitter( 
           chunk_size=450, # = 80–110 tokens(cioe' piu' o meno 80–110 parole )a
           chunk_overlap=50 # 50 is the sweet spot
         )
        #   /-------------/
        
      #   Questa unisce solo quando la prima parte finisce con una lettera spezzata:
        def clean_pdf_text(text: str) -> str:
         # unisce parole spezzate da hyphen + newline
            text = re.sub(r"-\s*\n\s*", "", text)
            # normalizza spazi multipli
            text = re.sub(r"\s+", " ", text)

            return text.strip()
        
      #   /-------------/

        def split_into_paragraphs(text: str) -> list[str]: 
             return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        #   /-------------/

        all_chunks = [] # stores all paragaph chunks of each pdf page
        

          # 🔴 PAGE OVERLAP QUI
        page_windows = build_page_windows(docs, window_size=2) # questa funzione crea nuovi Document con i dati
        # text,  page_Start, page_end.. metadata, e "non spezza" questi chunks se si estendono da una
        # pagina all'altra (tipo se un paragrafo inizia a pagina 3 e finisce a pagina 4) 
        # su questi dati si applicano poi il data cleaning e il semanting chunking definiti sotto
        
        for window_doc in page_windows: 
            
            # Facciamo il chunking semantico per ogni paragrafo del window(page 0,1 - page 2-3...)
            # Semantic chunking funziona meglio quando i testi sono localmente coerenti e 
            # appartengono alla stessa sezione / contesto (allo stesso window)
            # Unire pagina 2 con pagina 17 o capitolo 1 con capitolo 5, anche se “semanticamente simili”
            # rompe il contesto documentale, per questo uniamo per "windows chunks" 

            clean_paragraph_docs = [] # store all cleaned up paragraph docs for each window
            paragraphs = split_into_paragraphs(window_doc.page_content) # splittiamo i paragrafi all interno delle pagine pdf          
            
            for i, paragraph in enumerate(paragraphs): 
                 clean_parag_text = clean_pdf_text(paragraph)
          
                 para_doc = Document( # creiamo il documento per ogni paragrafo, con i dati testo, e metadati
                     page_content=clean_parag_text, # il paragrafo ricavato dalla function paragraph.(i chunks con i dati)
                     metadata={
                        **window_doc.metadata,
                        "paragraph_index": i 
                     }
                  )
                 
                 clean_paragraph_docs.append(para_doc)
                 
               #   para_chunks = splitter.split_documents([para_doc])
               #   all_chunks.extend(para_chunks)
        
        # Step 2: semantic chunking. Passiamo la collezione dei paragrafi, il modello per fare emb, e la treshold
        # alla funzione semantic_chunk_paragraphs, per fare semantic chunkings sui paragrafi "cleaned"
        # estratti sopra
            semantic_chunks = semantic_chunk_paragraphs( 
                 paragraph_docs=clean_paragraph_docs, # array contenente i dati 'cleaned',  'chunk_size e chunk_overlap', dove verra applicata la misurazione della dimilarita' semantica
                 # ed eventuale 'chunk union' se 2 o piu' paragrafy sono 'semanticamente simili' 
                 embeddings_model=embeddings_model, # in modello lo potremmo definire nella funzione stessa
                 sim_threshold=0.8,  # puoi regolare da 0.7 a 0.9
                 max_chars = 1200 # grandezza massima dei 'merged chunks'
            ) # il return di semantic_chunks e' un array contenent chunks uniti('merged') in base
            # alle loro similita' semantica(questi chunks arrivano fino a 1200 char, e solitamente 
            # equivalgono all'unione di 2-3 chunks), e chunks individuali 


         # Step 3: ulteriore split per lunghezza se necessario
        MAX_FINAL_CHUNK_CHARS = 1200

        for chunk in semantic_chunks:
            if len(chunk.page_content) <= MAX_FINAL_CHUNK_CHARS:
               all_chunks.extend(chunk) 
            # A questo elso non arriviamo mai per come e' conformato al momento il codice.
            # lo usiamo solo a scopo informativo e se # decidessimo di aumentare il max_char 
            # in semantic_chunk_paragraphs function
            else: 
                para_chunks = splitter.split_documents([chunk])
                all_chunks.extend(para_chunks)
               # qui' vengono raccolti i chunks finali, cioe' quei chunk
            # 'cleaned', definiti da 'chunk_size + chunk_overlap' e 'semanticamente selezionati', quindi
            # potenzialmente uniti se semanticamente simili. 
            # Questi dati finali verranno salvati su pinecone, dove la' avviene il semantic search

        for c in all_chunks[:5]:
            print("PAGE:", c.metadata.get("page_start"))
            print("PARAGRAPH:", c.metadata.get("paragraph_index"))
            print("TEXT:", c.page_content[:300])
            print("-" * 50)
         # 🧼 CLEANUP: unione chunk piccoli (non piu' necessaria)
      #   all_chunks = merge_small_chunks(all_chunks, min_size=250) # negli output print, non vediamo
     
      #  # 3️⃣ Connetti Pinecone con namespace = user_id (storage dei pdf di ogni diverso user)
      #   vectorstore = PineconeVectorStore( # Pinecone.from_existing_index(
      #      index_name=index_name, # deve eseistere. (usa index_name_large se vuoi usare il modello emb large)
      #      embedding=embeddings_model, # trasforma i chunks in embeddings
      #      namespace=user_id # inserire ordinatamente i dati nel db sotto la cartell user_id
      #    ) 

      #  # 4️⃣ Inserisci chunks
      #   vectorstore.add_documents(all_chunks) # trasforma i chunks in embeddings e inseriscili nel db (con id diverso  diverso ogni user, cosi' i dati pdf non si mescolano tra users)

      #   return {"message": f"{len(all_chunks)} chunks ingested for user {user_id}"}
    
    
   # 🧹 Pulizia file temporanei (best practice). rimuoviamo i file gia caricati in locale(C:\Users\ale\AppData\Local\Temp\tmpxxxx.pdf) in ingest.py
   #  per non incappare in errori. 

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

