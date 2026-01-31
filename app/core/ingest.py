# import os
# import pinecone
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain.document_loaders import PyPDFLoader
# from langchain.vectorstores import Pinecone
# from langchain.embeddings import OpenAIEmbeddings

# LEGGI SOTTO PRIMA DI RUNNARE QUESTO CODICE 

# # Inizializza Pinecone
# pinecone.init(
#     api_key=os.getenv("PINECONE_API_KEY"),
#     environment=os.getenv("PINECONE_ENVIRONMENT")
# )
# index_name = os.getenv("PINECONE_INDEX_NAME")

# embeddings_model = OpenAIEmbeddings() # quando non definito, OpenAIEmbeddings usa di default si usa = "text-embedding-3-small" che deve corrispondere all' index dimension=1536 quando andiamo a creare l'index. 
# text-embedding-3-small va bene per questo progetto demo. Se vuoi una migliore generazione della res e' un serch piu' accurato per pdf piu' complessi, usa text-embedding-3-large qui sotto. maggiori descrizioni su text-embedding nell file AboutEmbeddings_and_indexes.txt
# embeddings_model = OpenAIEmbeddings(model="text-embedding-3-large") # usiamo "text-embedding-3-large" se vogliamo usare embeddings piu' complessi, per pdf piu' complessi che danno un miglior data retriving

# def ingest_pdf(file_path: str, user_id: str):
#     # 1️⃣ Carica PDF
#     loader = PyPDFLoader(file_path)
#     docs = loader.load()

#     # 2️⃣ Chunking
#     splitter = RecursiveCharacterTextSplitter(
#         chunk_size=800,
#         chunk_overlap=150
#     )
#     chunks = splitter.split_documents(docs)

#     # 3️⃣ Connetti Pinecone con namespace = user_id
#     vectorstore = Pinecone.from_existing_index(
#         index_name=index_name,
#         embedding=embeddings_model,
#         namespace=user_id
#     )

#     # 4️⃣ Inserisci chunks
#     vectorstore.add_documents(chunks)

#     return {"message": f"{len(chunks)} chunks ingested for user {user_id}"}



# 🔹 Flusso corretto

# PDF caricati su S3

# Scarichi PDF nella tua app Python

# Chunking con LangChain (RecursiveCharacterTextSplitter)

# Generi embeddings con OpenAI (text-embedding-3-small)

# Crei index Pinecone da Python se non esiste ancora

# Inserisci embeddings nell’index (con namespace = user_id)