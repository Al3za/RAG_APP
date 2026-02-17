import os
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from dotenv import load_dotenv

from app.core.cosine_similarity_fun import cosine_similarity 

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

index_name = os.getenv("PINECONE_INDEX_NAME") # index per fare gli embeddings delle query (1536)
index = pc.Index(index_name)
print('index_name = ', index_name)

# model 3-small uguale al dimension definito nell' "index_name" che crea stessi embeddings dei chunks dei pdf
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small") 

# chat ci aiuta a formulare una risposta sensata in base ai 4 pdf chunks che piu' si assomigliano semanticamente all query(la domanda a chat) che lo user fa'
llm = ChatOpenAI( 
    model="gpt-4o-mini",
    temperature=0
)

## uncommente this block to see the chunks of your request:

# ------------------

# vectorstore = PineconeVectorStore(
#     index=index,
#     embedding=embeddings_model,
#     namespace="user_150"
# )

# query_embedding = embeddings_model.embed_query("ciao chat, riassumi brevemente di cosa si tratta l'argomento 'Problemi attuali della fisica'")
# results = vectorstore.index.query(
#     vector=query_embedding,
#     top_k=5,
#     namespace="user_150",
#     include_metadata=True,
#     include_values=False
# )

# for i, match in enumerate(results.matches):
#     print(f"Chunk {i+1} (score: {match.score})")
#     print(match.metadata["text"][:200])  # primi 200 caratteri

## uncommente this block above to see the chunks of your request:

# ----------------

# Grazie a langchain, in questo PROMPT addestriamo il modello a come rispondere in base alla domanda dello user(definita in  rag_chain:{question}), 
# e i dati della response di questa "question query", che corrispondono hai 4 chunks con piu' alta similarita' semantica 
# della  domanda fatta dallo user (i chunks della query definiti in  rag_chain:{context}) 

PROMPT = ChatPromptTemplate.from_template("""
You are a careful and precise assistant.

Answer the question using ONLY the information provided in the context.
The context may contain information from different pages or sections of the document.
If relevant information appears in multiple parts, combine them into a single,
coherent explanation.

Do NOT use external knowledge.
If the context does not explicitly support the answer, say "I don't know."
Do not infer beyond what is directly stated.

Context:
{context}

Question:
{question}
""") 
# OpenAIEmbeddings(model="text-embedding-3-small") e model="gpt-4o-mini" distingue bene anche se il pdf e' in linguaggio
# misto


# Sintesi

# Non è strano che una domanda semplice dia punteggi ~0.7: il modello embedding piccolo + MMR + caratteri PDF “sporchi” abbassa la similarità.

# Con soglia 0.75 → “I don’t know”

# Soluzione pratica: abbassare soglia a 0.65–0.70, pulire meglio i chunk, eventualmente usare embedding più grande.


def ask_question(user_id: str, question: str):

    vectorstore = PineconeVectorStore(
        index=index,
        embedding=embeddings_model, 
        namespace=user_id,
        text_key="text"
    )
    
    # Recupera chunk con MMR:
    retriever = vectorstore.as_retriever(
        search_type="mmr", 
        search_kwargs={ 
            "k": 8, # 5-7 va bene. (Spesso 5 è più che sufficiente e riduce rumore.)
            # "filter": {"user_id": user_id}, 
            "fetch_k": 15, 
            "lambda_mult":0.8 # (0.5 per iniziare). 0.7 porta più peso alla similarità, 
            # meno alla diversità e spesso migliora precisione.
        }
    ) 
    question_docs = retriever.invoke(question) # qui ci ssono i top 5 semantic_chunks pdf correlati alla query
   
    # Calcola embedding della query
    query_embedding = embeddings_model.embed_query(question)

    # Calcola score manualmente
    filtered_docs = []

    for doc in question_docs: # usiamo la funzione cosine_similarity per filtrare i chunks della query
        # in modo da avere solo quelli > 0.75
        chunk_embedding = embeddings_model.embed_query(doc.page_content) # il content di ognuno dei top 5 chunk
        score = cosine_similarity(query_embedding, chunk_embedding) # misuriamo la similarita semantica

        print("Score:", score)

        if score >= 0.58: # 0.75 è un buon punto iniziale. 0.78–0.80 è più conservativo
            filtered_docs.append(doc) # solo i chunk importanti. Ora invece di 5 chunk, avremo magari
            # solo 3, ma saranno molto rilevanti rispetto alla query

    if not filtered_docs: # se nemmeno 1 chunk e > 0.75 (quindi nemmeno 1 chunk abbastanza rilevante alla query)
       return {"answer": "I don't know based on the provided context."}
    
    # docs_debugg = retriever.invoke(question)

    print("\n--- CHUNKS RECUPERATI ---\n")
    for i, d in enumerate(filtered_docs):
        print(f"\nChunk {i+1}")
        print("Page:", d.metadata.get("page"))
        print("Paragraph index:", d.metadata.get("paragraph_index"))
        print(d.page_content)


       # 2️⃣ RAG chain moderna (LCEL)
    rag_chain = (
        {
            "context": retriever,
            "question": RunnablePassthrough()
        }
        | PROMPT
        | llm
        | StrOutputParser()
    )

    answer = rag_chain.invoke(question) # qua llm processa la query e' la response di pinecone come definito in PROMPT, e' ritorna una risponsa sensata con questi dati

    return {
        "answer": answer
    }