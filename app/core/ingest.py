import os
from dotenv import load_dotenv 

# from langchain_pinecone import Pinecone as LC_Pinecone
from langchain_pinecone import PineconeVectorStore, Pinecone
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
# from langchain_community.vectorstores import Pinecone
from langchain_openai import OpenAIEmbeddings # il modello AI per creare embeddings semantici
from pinecone import Pinecone, ServerlessSpec # SDK Pinecone

from uuid import uuid4

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
    try:
    # 1️⃣ Carica PDF
       loader = PyPDFLoader(file_path)
       docs = loader.load()

       # 2️⃣ Chunking
       splitter = RecursiveCharacterTextSplitter(
          chunk_size=800, # 1 chunk = 800 caratteri (130–160 parole) Un PDF universitario di 10–20 pagine di solito produce: 80–200 chunks circa
          chunk_overlap=150
         )
       chunks = splitter.split_documents(docs)

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
       vectorstore.add_documents(chunks) # trasforma i chunks in embeddings e inseriscili nel db (con id diverso  diverso ogni user, cosi' i dati pdf non si mescolano tra users)

       return {"message": f"{len(chunks)} chunks ingested for user {user_id}"}
    
    
   # 🧹 Pulizia file temporanei (best practice). rimuoviamo i file gia caricati in locale(C:\Users\ale\AppData\Local\Temp\tmpxxxx.pdf) in ingest.py
   #  per non incappare in errori. 

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)




 # Retrieval (similarity search):

#  Quando lo user fa' la query su Pinecone, la query stessa viene trasformata in embedding dallo stesso modello che abbiamo usato per dare
# gli embeddings dei chunks pdf (embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")).  Dopo la trasformazione della query in embedding,
# Pinecone(non il modello di openai) fa la ricerca per similarita' tra gli emb della query e quella dei chunks del pdf file(chiamata cosine similarit), 

