import os
import re
import unicodedata
from dotenv import load_dotenv 

from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore, Pinecone
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings # il modello AI per creare embeddings semantici
from pinecone import Pinecone, ServerlessSpec # SDK Pinecone
from app.core.cosine_similarity_fun import semantic_chunk_paragraphs
from app.core.merge_broke_sentence_cross_page import merge_broken_sentences
from app.core.pre_post_merge_small_parag import post_merge_semantic_small_chunks, pre_merge_small_paragraphs
from app.utils.rate_limiter import ingest_status
# from app.core.page_overlap  import build_page_windows

# NEL FILE ingest_desc.py VIENE SPIEGATO DETTAGLIATAMENTE COSA AVVIENE IN QUESTO FILE RIGA PER RIGA

load_dotenv()

# # Inizializza Pinecone SDK

# 1️⃣ Crea istanza Pinecone SDK
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# 2️⃣ Index name dal .env
index_name = os.getenv("PINECONE_INDEX_NAME") # gia creato sotto, basta crearlo 1 volta per questo e' commentato


embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")

def ingest_pdf(file_path: str, namespace: str):

    try:
        # print('user_id = ', user_id)
    # 1️⃣ Carica PDF
        loader = PyPDFLoader(file_path) 
        docs = loader.load() # docs = raccolta in formato Document di tutte la pagine del pdf
          #   /-------------/
       # 2️⃣ Chunking
        splitter = RecursiveCharacterTextSplitter( 
           chunk_size=450, 
           chunk_overlap=50 
         )
        #   /-------------/
        
      #   Questa unisce solo quando la prima parte finisce con una lettera spezzata:
        def clean_pdf_text(text: str) -> str: # clean each pdf page

            # Mette gli accenti e apostrofi al posto giusto
            text = unicodedata.normalize("NFC", text)

         # unisce parole spezzate da hyphen + newline
            text = re.sub(r"-\s*\n\s*", "", text)

            # parola spezzata da newline senza hyphen
            text = re.sub(
               r'(\b\w{1,3})\n(\w{2,}\b)',
               r'\1\2',
               text
            )

            return text
        
         
        def fix_pdf_characters(text: str) -> str: # correggere gli errori tipo pi u, cos ı`
            # sostituisci backtick usati come apostrofi
            text = text.replace("`", "'")
            text = text.replace("´", "'")
            text = text.replace("’", "'")  # normalizza apostrofi curvi
            # sostituisci caratteri strani ricorrenti (tipo ı → i)

            # casi tipo: pi' u  → più
            text = re.sub(r"'\s+u\b", "ù", text)
            text = re.sub(r"'\s+a\b", "à", text)
            text = re.sub(r"'\s+e\b", "è", text)
            text = re.sub(r"'\s+i\b", "ì", text)
            text = re.sub(r"'\s+o\b", "ò", text)
        
            # casi tipo: propriet' a → proprietà
            text = re.sub(r"'\s+a\b", "à", text)
        
         
            text = text.replace("ı", "i")
            text = text.replace("ˆ", "")  # rimuove circonflessi sparsi
            # puoi aggiungere altri pattern specifici
            return text

        # splittiamo solo se:
        # punto + newline + Maiuscola
        # + riga relativamente corta (< 80 caratteri prima del prossimo newline)
        def split_into_paragraphs(text):

            text = text.strip()
        
            # 1️⃣ Unisci line-break interni (ma NON dopo punto)
            text = re.sub(r'(?<!\.)\n(?=[a-zàèéìòù])', ' ', text)

            # 2️⃣ Trasforma linee composte solo da simboli in doppio newline
               # Esempio: "* * *"  oppure  "***"  oppure "---"
            text = re.sub(
                r'\n\s*[^A-Za-z0-9À-ÖØ-öø-ÿ]+\s*\n',
                '\n\n',
                text
            )

            # rimuovi duplicati
            # text = re.sub(r'(\b.+?\b)( \1)+', r'\1', text) puoi' provarlo piu' avanti, anche se 
            # duplicati =< 80 chars non sono un problema per embeddings o llm 
        
            # 2️⃣ Split principale (PDF classici)
            paragraphs = re.split(r'\n\s*\n', text)
        
            refined = []
        
            for p in paragraphs:
                p = p.strip()
        
                # 3️⃣ Split secondario SOLO se sembra vero nuovo paragrafo
                sub_paragraphs = re.split(
                    r'(?<=\.)\n(?=[A-ZÀÈÉÌÒÙ][^\.]{0,80}\n)',
                    p
                )
        
                for sp in sub_paragraphs:
                    refined.append(sp.strip())
        
            return [p for p in refined if p]



        all_chunks = []
        
        clean_paragraph_docs = [] 
        

        for page_idx, doc in enumerate(docs): 
            cleaned_pdf_text = clean_pdf_text(doc.page_content)
            cleaned_pdf_text = fix_pdf_characters(cleaned_pdf_text)
            paragraphs = split_into_paragraphs(cleaned_pdf_text)
            
            # cleaned_pdf_text = clean_pdf_text(doc.page_content)
            # paragraphs = split_into_paragraphs(cleaned_pdf_text) # non sempre riconosce i paragrafi se 
            
            paragraph_docs = [ # i documenti dei paragrafi (o blocco pagina intero se paragrafi non esistono), per ogni pagina del pdf
                Document(
                    page_content=para,
                    metadata={
                    #    "source": filename, # Da inserire
                       "page": page_idx,
                       "page_start": page_idx,
                       "page_end": page_idx,
                       "paragraph_index": i,
                       "chunk_id": f"{page_idx}_{i}" # Da inserire
                }
               )
               for i, para in enumerate(paragraphs)
            ]

            # 3️⃣ merge cross-page chunks (il primo doc split. Una specie di semi semantico split, che
            # poi verra ulteriormente 'chunked' con overlap)
            paragraph_docs = merge_broken_sentences(paragraph_docs) # Guarda se l’ULTIMO CHUNK 
            # finisce con punteggiatura forte e se il next inizia con una maiuscola. Se non lo fanno,
            # questa function unisce questi chunk se non 'sfora' il MAX_MERGE_LEN chars. questa pratica
            # Aumenta logica semantica tra i chunks e crea unisce 2 chunks per un massimo di 900 chars

            # 4️⃣ split in small chunks con overlap e append diretto in clean_paragraph_docs
            for para_doc in paragraph_docs:
                text_len = len(para_doc.page_content)

                if text_len > 450:
                    # split con il tuo splitter (gestisce max_chars + overlap)
                    small_chunks = splitter.split_documents([para_doc])
                    for chunk in small_chunks:
                        # aggiorniamo metadata se vuoi, qui manteniamo quello originale
                        clean_paragraph_docs.append(chunk)
                else:
                    # chunk corto rimane così com'è. Qui non abbiamo bisogno di overlap perche' se' il chunk e <130 chars verra' merged
                    # nella fun pre_merge_small_paragraphs, se invece e' > 130 e < 450, ed simile al suo next chunk, questi verranno comunque merged  
                    # infine, se non se questo small chunk non viene merged in questi due casi, puo' venir 'merged' alla fine in "post_merge_semantic_small_chunks"
                    # cerchiamo in piu' modi logici di unire i piccoli chunks perche potrebbero creare embeddings
                    # inutili e dannosi per il nostro rag app
                    clean_paragraph_docs.append(para_doc)       
   

        clean_paragraph_docs = pre_merge_small_paragraphs( 
            clean_paragraph_docs, 
            min_chars=130,
            max_chars=600
        )

        # print('clean_paragraph_docs =',clean_paragraph_docs) # 83 chunks totali

        CROSS_PAGE_OVERLAP = 50
        
        for i in range(1, len(clean_paragraph_docs)): 
            current_doc = clean_paragraph_docs[i] 
            prev_doc = clean_paragraph_docs[i - 1]
            
            if prev_doc.metadata.get("page_end") != current_doc.metadata.get("page_start"):
               
               # Prendiamo gli ultimi 50 chars del precedente
               prefix = prev_doc.page_content[-CROSS_PAGE_OVERLAP:]
            
               # Evitiamo doppie duplicazioni (se la pagina ha gia overlap, ma questo non avviene mai dato
            #    il chunk page by page di default)
               if not current_doc.page_content.startswith(prefix):
                
                   current_doc.page_content = prefix + " " + current_doc.page_content
                   current_doc.metadata["page_start"] = prev_doc.metadata["page_start"]
                #    current_doc.metadata["page_end"] = current_doc.metadata["page_end"]
               

          
        # print('pre_clean_paragraph_docs_overflow =',clean_paragraph_docs) # 83 chunks totali
        
    #    # NON AVREMO BISOGNO SI PAGE_WINDOW OVERLAP, PERCHE' qui andiamo ad unire i chunks semanticamente
    #    # simili anche se si trovano in pagine differenti. Dopodiche' raccogliamo i top 5 chunks 
    #    # piu' correlati alla query dello user (la domanda che l'utente fa' al llm dopo aver caricato il pdf)
    #    # e cosi' llm andra' a formulare riposte soddisfacenti(retrival)

        semantic_chunks = semantic_chunk_paragraphs( 
            paragraph_docs=clean_paragraph_docs, 
                
            embeddings_model=embeddings_model, 
            sim_threshold=0.65, # sweet spot per fare merge dei chunks
            max_chars = 1200 
            )
        
        # print('semantic_chunks here = ', semantic_chunks ) # 64 chunk (da 83 a 64 perche alcuni si sono uniti perche' semanticamente simili)
        
        

        semantic_chunks = post_merge_semantic_small_chunks( 
            semantic_chunks,
            min_chars=250,  
            max_chars=1200  # 1200 chars è un buon limite per mantenere la precisione degli embeddings, ma puoi regolarlo in base alle tue esigenze specifiche
            )

        # print('post semantic_chunks here = ', semantic_chunks ) # 53 chunks

       
        # total_semantic_chars_before = sum(len(c.page_content) for c in semantic_chunks)
        # total_semantic_chars_after_final_merge = sum(len(c.page_content) for c in semantic_chunks)

        

        # print(f"Total chars in semantic chunks before final merge: {total_semantic_chars_before}")
        # print(f"Total chars in semantic chunks after final merge: {total_semantic_chars_after_final_merge}")

    #     # #  # Step 3: ulteriore split per lunghezza se necessario
        MAX_FINAL_CHUNK_CHARS = 1200 # numero massimo di chars per semantic_chunks. Oltre, gli embeddings creati perderebbero di precisione

        for chunk in semantic_chunks:
            if len(chunk.page_content) <= MAX_FINAL_CHUNK_CHARS: # nel caso post_merge_small_chunks facesse sforare
             
                 all_chunks.append(chunk)
                #  all_chunks.extend(para_chunks) # ERRATO. chunk è un Document, non una lista.
                # extend(chunk) prova a iterare su chunk → risultato non definito / corrotto.
            else:  # never reach this else for now because all chunks are < 1200 chars, ma è una buona safety check comunque
                 print(f"⚠️ Chunk too long ({len(chunk.page_content)} chars), splitting further...")
                 para_chunks = splitter.split_documents([chunk])
                 all_chunks.extend(para_chunks)
                

        # #     #   debugg
        # for i, c in enumerate(all_chunks[:40]): # prendi 5 chunks
        #      print(f"CHUNK #{i}")
        #      print("PAGES:", c.metadata.get("page_start"), "→", c.metadata.get("page_end")) # i metadati definiti da noi in page?overlap.py
        #      print("PARAGRAPH:", c.metadata.get("paragraph_index"))
        #      print("CHUNK LEN:", len(c.page_content))
        #      print("TEXT:", c.page_content)
        #      print("-" * 50)
        #      if len(c.page_content) < 200:
        #          print("⚠️ SMALL CHUNK DETECTED")
     
    #    3️⃣ Connetti Pinecone con namespace = user_id (storage dei pdf di ogni diverso user)
        vectorstore = PineconeVectorStore( 
           index_name=index_name, # deve eseistere. (usa index_name_large se vuoi usare il modello emb large)
           embedding=embeddings_model, # trasforma i final chunks in embeddings prima dello storage in pinecone
           namespace= namespace #user_id # inserire ordinatamente i dati nel db sotto la cartell user_id
         ) 
        
        # Cancella i chunks vecchi nello stesso namespace
        vectorstore.delete(filter={"chunk_id": {"$exists": True}}) #  elimina tutti i documenti nel namespace dell'utente

    #    # 4️⃣ Inserisci chunks
        vectorstore.add_documents(all_chunks) # trasforma i chunks in embeddings e inseriscili nel db (con id diverso  diverso ogni user, cosi' i dati pdf non si mescolano tra users)
        ingest_status(namespace,'ready') # gli argomenti da passare a redis per il frontend

        # return {"message": f"{len(all_chunks)} chunks ingested for user {namespace}"} # return noo needed
    
    except Exception as e:
        ingest_status(namespace,'error')
        print("Ingest error:", e)
    
   # 🧹 Pulizia file temporanei (best practice). rimuoviamo i file gia caricati in locale(C:\Users\ale\AppData\Local\Temp\tmpxxxx.pdf) in ingest.py
   #  per non incappare in errori. 
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

