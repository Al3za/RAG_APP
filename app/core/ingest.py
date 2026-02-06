import os
import re
from dotenv import load_dotenv 

# from langchain_pinecone import Pinecone as LC_Pinecone
from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore, Pinecone
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
# from langchain_community.vectorstores import Pinecone
from langchain_openai import OpenAIEmbeddings # il modello AI per creare embeddings semantici
from pinecone import Pinecone, ServerlessSpec # SDK Pinecone
from app.core.merge_small_chunk import merge_small_chunks
from app.core.page_overlap  import build_page_windows


load_dotenv()

# # Inizializza Pinecone SDK

# 1️⃣ Crea istanza Pinecone SDK
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# 2️⃣ Index name dal .env
# index_name = os.getenv("PINECONE_INDEX_NAME", "rag-pdf-index") # use rag-pdf-index the first time  you create an index
index_name = os.getenv("PINECONE_INDEX_NAME") # gia creato sotto, basta crearlo 1 volta per questo e' commentato

# index_name_large = os.getenv("PINECONE_INDEX_NAME_LARGE"). gia' creato, usalo quando vuoi usare emb large

# index_name_large = "rag-pdf-index-large" # creiamo un index con embeddings model large, che e' piu' lento di small. ma piu' forte e' preciso

# # # 3️⃣ Crea index se non esiste
# existing_indexes = [i.name for i in pc.list_indexes()]
# if index_name not in existing_indexes: # if index_name_large
#     pc.create_index(
#         name=index_name, # name = index_name_large
#         dimension=1536,   # (cambia in 3072 per large "text-embedding-3-large")   # per text-embedding-3-small, (leggi file core/AboutEmbeddings_and_indexes.txt )
#         metric="cosine",
#         spec=ServerlessSpec(
#             cloud="aws",
#             region="us-east-1"  # free tier
#         )
#     )
#     print(f"Index '{index_name}' creato ✅")
# else:
#     print(f"Index '{index_name}' già esistente ✅")

# print("Indexes attuali:", [i.name for i in pc.list_indexes()])

# embeddings_model = OpenAIEmbeddings() # quando non definito, OpenAIEmbeddings usa di default si usa = "text-embedding-3-small" che deve corrispondere all' index dimension=1536 quando andiamo a creare l'index. 
# # text-embedding-3-small va bene per questo progetto demo. Se vuoi una migliore generazione della res e' un serch piu' accurato per pdf piu' complessi, usa text-embedding-3-large qui sotto. maggiori descrizioni su text-embedding nell file AboutEmbeddings_and_indexes.txt
# embeddings_model = OpenAIEmbeddings(model="text-embedding-3-large") # usiamo "text-embedding-3-large" se vogliamo usare embeddings piu' complessi, per pdf piu' complessi che danno un miglior data retriving



embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
# embeddings_model = OpenAIEmbeddings(model="text-embedding-3-large") # per pdf piu' complessi e 
# migliore generazine di res e anche miglior search (leggi file core/AboutEmbeddings_and_indexes.txt)


def ingest_pdf(file_path: str, user_id: str):
    # PDF-aware chunking. (✔️ è uno step di normalizzazione strutturale prima della semantica) 
    # Il PDF-aware chunking non cerca ancora di capire il significato (Abstract, Introduction, ecc.)
    # ma rispetta la struttura fisica del PDF (pagine,paragrafi, line break, layout)
    try:
        print('user_id = ', user_id)
    # 1️⃣ Carica PDF
        loader = PyPDFLoader(file_path) # PyPDFLoader si assicura che  che ogni Document(docs sotto) è UNA pagina del pdf la quale poi viene  applicato il chunking
        docs = loader.load() # ogni docs equivale a una pagina del pdf. poi sotto per ognuna di queste pagine facciamo il chung di 800 caratteri 
    #    print('docs here:', docs) 
#      docs = [
       #   Document(page_content=(text della pagina_0), metadata={"page": 0}),
       #   Document(page_content=(text della pagina_1), metadata={"page": 1),
       #   Document(page_content=(text della pagina_2), metadata={"page": 2),
       #   ...
       # ]

       # 2️⃣ Chunking
        splitter = RecursiveCharacterTextSplitter(
           chunk_size=800, # 1 chunk = 800 caratteri (130–160 parole) Un PDF universitario di 10–20 pagine di solito produce: 80–200 chunks circa
           chunk_overlap=150
         )
        
      #   Questa unisce solo quando la prima parte finisce con una lettera spezzata:
        def clean_pdf_text(text: str) -> str:
         # unisce parole spezzate da hyphen + newline
            text = re.sub(r"-\s*\n\s*", "", text)

            # normalizza spazi multipli
            text = re.sub(r"\s+", " ", text)

            return text.strip()
 
      # questa fun riconosce i paragrafi. Perche in un pdf standard, i paragrafi sono separati quasi sempre da 
      # "doppio capo"(1 volta Ctrl+Enter), "doppio capo"(2 volte Ctrl+Enter), 
      # oppure da piu volte (N volte Ctrl+Enter). questo viene catturato dal re.split(r"\n\s*\n", text), e cosi
      # sappiamo dove fare il chunking per paragrafo 
      # Quindi questo detta la fine di un paragrafo e una separazione logica
        def split_into_paragraphs(text: str) -> list[str]: 
             return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    
        all_chunks = [] # stores all paragaph chunks of each pdf page
        
          # 🔴 PAGE OVERLAP QUI
        page_windows = build_page_windows(docs, window_size=2) # quest funzione crea nuovi Document
        # cosi uniamo i docs: [pagina0,pagina1],[pagina1,pagina2].... guarda la desription nel file della fun
        # questo e' il return :
      #   page_windows = [
      #     Document(pagine 0–1),
      #     Document(pagine 1–2),
      #     Document(pagine 2–3),
      #      ...
      #    ]. In poche parole, in questa funzione passiamo ogni docs a questa funzione,
      #  dove qui uniamo a coppia(page:(0,1),(1,2),(2,3),(3,4)) i "text data" delle pagine del pdf(che si trovano in: docs.page_content),
      #  e poi creaiamo i metadata per ognuna di queste pagine accoppiate queste pagine accoppiate 
        
        for window_doc in page_windows: 
            # e qui facciamo lo split dei paragrafi che si trovano entro le "pagine accoppiate" 
            # create nella var page_windows. Tutto questo serve a prevenire il problema della "troncatura
            # del paragrafo", nel caso un paragrafo e' sparso in piu' pagine (ad esempio mezzo paragrafo si trova
            # alla fine della pagina tre e l'altro mezzo all inizio della pagina 4). questo potrebbe creare
            # chunks non proprio semantici, perche senza questa tecnicha di "page overlap", non ci sarebbe 
            # overlapp tra in questo paragrafo, portanto "confusione" dovuta alla possibile mancanza di semanticita'
            # e quindi "possibili bad retrival"
            paragraphs = split_into_paragraphs(window_doc.page_content) # splittiamo i paragrafi all interno delle pagine pdf          
           
           

            for i, paragraph in enumerate(paragraphs): # trasformare ogni paragrafo qui sotto in un Document, con i metadati della page del pdf (page, section, document). ottimo per metadati e per poter fare semantic chunking
                 
                 # call the function that clears the paragraph tho avoid fractured words(teach ers) that will not be good storing in 
                 # pinecone because it can be bad for the semantic search on the db
                 clean_parag_text = clean_pdf_text(paragraph)
            #   A cosa serve creare para_doc?
            #   1) trasformare ogni paragrafo(paragraph) in una unità indipendente
            #   2) mantenere numero di pagina e posizione del paragrafo nella pagina (per i metadati credo)
            # Cosi' non spezzi mai un paragrafo a metà, e il chunking successivo è più pulito
                 para_doc = Document(
                     page_content=clean_parag_text, # il paragrafo ricavato dalla function paragraph.(i chunks con i dati)
                     metadata={
                        **window_doc.metadata, # i metadati descritto nella func build_page_windows. 
                        # {"page_start": 3,"page_end": 4,"source": "file.pdf"} 
                        # questi metadati di dicono dove si trova il chunk del paragrafo, cosi, 
                        # se questo chunk si estende su piu' pagine, e' correttamente riportato nei metadati
                        "paragraph_index": i 
                     }
                  )

          ## facciamo i chunks di ognuno di questi singoli paragrafi paginatizati con para_doc.
          # se è corto → 1 chunk
          # se è lungo → più chunk (800 char, overlap 150)
                 para_chunks = splitter.split_documents([para_doc])
        #    pushamo questi chunk finali alla lista globale all_chunks ( in js = all_chunks.push(para_chunks))
                 all_chunks.extend(para_chunks)
        
         # 🧼 CLEANUP: unione chunk piccoli
        all_chunks = merge_small_chunks(all_chunks, min_size=250) # negli output print, non vediamo
        # paragraph_index = 0 (titolo della prima pagina )
        # paragraph_index = 1 (la parte "abstract")
        # paragraph_index = 2 (e' l'attuale testo dell' abstract)
        # questo perche lo abbiamo specificato in merge_small_chunks, che se i paragrafi sono piccoli,
        # i dati di questo paragrafo lo uniamo al primo chunk che e' > a 250 caratteri, in questo caso il
        # chunk dove e descritto "abstract". infatti questo chunk contiene titolo, "abstract", e il text
        # di "abstract". ed e' il paragraph_index 0  
 
        # debugg
      #   for i, c in enumerate(all_chunks[:8]): # prendi 5 chunks
      #        print(f"CHUNK #{i}")
      #        print("PAGES:", c.metadata.get("page_start"), "→", c.metadata.get("page_end")) # i metadati definiti da noi in page?overlap.py
      #        print("PARAGRAPH:", c.metadata.get("paragraph_index"))
      #        print("CHUNK LEN:", len(c.page_content))
      #        print("TEXT:", c.page_content)#[:200])
      #        print("-" * 50)
      #        if len(c.page_content) < 200:
      #            print("⚠️ SMALL CHUNK DETECTED")

     

       # 3️⃣ Connetti Pinecone con namespace = user_id (storage dei pdf di ogni diverso user)
        vectorstore = PineconeVectorStore( # Pinecone.from_existing_index(
           index_name=index_name, # deve eseistere. (usa index_name_large se vuoi usare il modello emb large)
           embedding=embeddings_model, # text-embedding-3-small (lo cambieremo con large. ricorda di creare un nuovo index settato per large)
        # embedding trasforma Ogni chunk in un vettore numerico "semantico" grazie al modello text-embedding-3-small di OpenAIEmbeddings:
        # (model="text-embedding-3-small") che e' stato allenato apposta. ricorda che text-embedding-3-large e' migliore, e che in futuro
        #  andremo ad usare questo
           namespace=user_id # inserire ordinatamente i dati nel db sotto la cartell user_id
         ) 

       # 4️⃣ Inserisci chunks
        vectorstore.add_documents(all_chunks) # trasforma i chunks in embeddings e inseriscili nel db (con id diverso  diverso ogni user, cosi' i dati pdf non si mescolano tra users)

        return {"message": f"{len(all_chunks)} chunks ingested for user {user_id}"}
    
    
   # 🧹 Pulizia file temporanei (best practice). rimuoviamo i file gia caricati in locale(C:\Users\ale\AppData\Local\Temp\tmpxxxx.pdf) in ingest.py
   #  per non incappare in errori. 

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)




 # Retrieval (similarity search):

#  Quando lo user fa' la query su Pinecone, la query stessa viene trasformata in embedding dallo stesso modello che abbiamo usato per dare
# gli embeddings dei chunks pdf (embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")).  Dopo la trasformazione della query in embedding,
# Pinecone(non il modello di openai) fa la ricerca per similarita' tra gli emb della query e quella dei chunks del pdf file(chiamata cosine similarit), 

