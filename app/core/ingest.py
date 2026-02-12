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
from app.core.merge_broke_sentence_cross_page import merge_broken_sentences
from app.core.pre_post_merge_small_parag import post_merge_small_chunks, pre_merge_small_paragraphs
# from app.core.page_overlap  import build_page_windows

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
        loader = PyPDFLoader(file_path) 
        docs = loader.load() 
          #   /-------------/
       # 2️⃣ Chunking
        splitter = RecursiveCharacterTextSplitter( 
           chunk_size=450, 
           chunk_overlap=50 
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

        def split_into_paragraphs(text):
             # Unisci linee spezzate
             text = re.sub(r'\n(?=[a-zàèéìòù])', ' ', text)

             # Poi dividi sui veri paragrafi
             paragraphs = re.split(r'\n\s*\n', text)

             return [p.strip() for p in paragraphs if p.strip()]

        #   /-------------/

        all_chunks = []
        
        clean_paragraph_docs = [] 

          # 🔴 PAGE OVERLAP QUI
        # page_windows = build_page_windows(docs, window_size=2) 
        

        for page_idx, doc in enumerate(docs): 
            # Controlliamo se una pagina pdf contenga paragrafi o se e' un singolo blocco di testo
            # e' possibile che non ci sia nemmeno un paragrafo nella pagina pdf che stiamo analizando
            # e sotto preveniamo che non creiamo un document che equivale un intera pagina
            paragraphs = split_into_paragraphs(doc.page_content) 
            # clean_chunks = clean_pdf_text(paragraphs_docs)

            for i, paragraph_text in enumerate(paragraphs):

                 if len(paragraph_text) > 450: # se la pagina pdf e' un singolo blocco testo, o se
                     # e' composta da 2 grandi paragrafi di ad esempio 1300 char o piu' ciascuno
                     # la suddividiamo in chunk di 450 per evitare piu' avanti di avere embeddings 
                     # troppo grandi e quindi imprecisi per semanti chunking e bad retrival 
                     small_chunks = splitter.split_documents([Document(page_content=paragraph_text)]) # lista document
                     for chunk in small_chunks: # prendi le stringe di questi documents
                         clean_paragraph_docs.append(
                             Document(
                                page_content=chunk.page_content, # text di ogni documente
                                metadata={
                                    "page":page_idx,
                                    "page_start": page_idx,
                                    "page_end": page_idx,
                                    "paragraph_index": i  
                                }
                              )
                          )
                 else: # se i paragrafi esistono e sono < 450 char, vengono mantanuti come sono, e poi eventualmente
                     # se troppo piccoli verranno 'merged' con gli altri chunks se z 130 chat (funzione pre_merge_small_paragraphs)
                    #  small_chunks = paragraph_doc
                     clean_paragraph_docs.append(
                        Document( 
                           page_content= paragraph_text, # text del doc
                           metadata={
                              "page":page_idx,
                              "page_start": page_idx,
                              "page_end": page_idx,
                              "paragraph_index": i  
                           }
                        )   
                      )
                #  clean_paragraph_docs.append(para_doc)

       
       # Se un chunk inizia nella pagina 3 e prosegue nella pagina 4, questa funzione non spezza
       # il chunk, ma li unisce(unione chunks cross page)
        clean_paragraph_docs = merge_broken_sentences(clean_paragraph_docs)         
   
        # unisce chunks < 130 char con il chunk precedente
        clean_paragraph_docs = pre_merge_small_paragraphs( 
            clean_paragraph_docs,
            min_chars=130,
            max_chars=600
        )
        # print('clean_paragraph_docs =',clean_paragraph_docs)

       # NON AVREMO BISOGNO SI PAGE_WINDOW OVERLAP, PERCHE' qui andiamo ad unire i chunks semanticamente
       # simili anche se si trovano in pagine differenti. Dopodiche' raccogliamo i top 5 chunks 
       # piu' correlati alla query dello user (la domanda che l'utente fa' al llm dopo aver caricato il pdf)
       # e cosi' llm andra' a formulare riposte soddisfacenti(retrival)
        semantic_chunks = semantic_chunk_paragraphs( 
            paragraph_docs=clean_paragraph_docs, 
                
            embeddings_model=embeddings_model, 
            sim_threshold=0.65, # sweet spot per fare merge dei chunks
            max_chars = 1200 
            )

        # semantic_chunks = post_merge_small_chunks( 
        #     semantic_chunks,
        #     min_chars=250,  
        #     max_chars=1200 
        #     )


        #  # Step 3: ulteriore split per lunghezza se necessario
        MAX_FINAL_CHUNK_CHARS = 1200 # numero massimo di chars per semantic_chunks. Oltre, gli embeddings creati perderebbero di precisione

        for chunk in semantic_chunks:
            if len(chunk.page_content) <= MAX_FINAL_CHUNK_CHARS: # nel caso post_merge_small_chunks facesse sforare
             
                 all_chunks.append(chunk)
                #  all_chunks.extend(para_chunks) # ERRATO. chunk è un Document, non una lista.
                # extend(chunk) prova a iterare su chunk → risultato non definito / corrotto.
            else:  # never reach this else for now
                 para_chunks = splitter.split_documents([chunk])
                 all_chunks.extend(para_chunks)
                

            #   debugg
        for i, c in enumerate(all_chunks[:40]): # prendi 5 chunks
             print(f"CHUNK #{i}")
             print("PAGES:", c.metadata.get("page_start"), "→", c.metadata.get("page_end")) # i metadati definiti da noi in page?overlap.py
             print("PARAGRAPH:", c.metadata.get("paragraph_index"))
             print("CHUNK LEN:", len(c.page_content))
             print("TEXT:", c.page_content)
             print("-" * 50)
             if len(c.page_content) < 200:
                 print("⚠️ SMALL CHUNK DETECTED")
        #  🧼 CLEANUP: unione chunk piccoli (non piu' necessaria)
     
    #    # 3️⃣ Connetti Pinecone con namespace = user_id (storage dei pdf di ogni diverso user)
    #     vectorstore = PineconeVectorStore( # Pinecone.from_existing_index(
    #        index_name=index_name, # deve eseistere. (usa index_name_large se vuoi usare il modello emb large)
    #        embedding=embeddings_model, # trasforma i chunks in embeddings
    #        namespace=user_id # inserire ordinatamente i dati nel db sotto la cartell user_id
    #      ) 

    #    # 4️⃣ Inserisci chunks
    #     vectorstore.add_documents(all_chunks) # trasforma i chunks in embeddings e inseriscili nel db (con id diverso  diverso ogni user, cosi' i dati pdf non si mescolano tra users)

    #     return {"message": f"{len(all_chunks)} chunks ingested for user {user_id}"}
    
    
   # 🧹 Pulizia file temporanei (best practice). rimuoviamo i file gia caricati in locale(C:\Users\ale\AppData\Local\Temp\tmpxxxx.pdf) in ingest.py
   #  per non incappare in errori. 

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

