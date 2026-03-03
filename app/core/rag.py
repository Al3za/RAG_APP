import os
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from app.utils.extract_page import extract_page_info

from dotenv import load_dotenv 

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

index_name = os.getenv("PINECONE_INDEX_NAME") # index per fare gli embeddings delle query (1536)
index = pc.Index(index_name)
# print('index_name = ', index_name)

# model 3-small uguale al dimension definito nell' "index_name" che crea stessi embeddings dei chunks dei pdf
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small") # Crea gia' ottimi embeddings, va bene per questo progetto personale
# embeddings_model = OpenAIEmbeddings(model="text-embedding-3-large") # Crea embeddings piu' precisi, anche su chunks piu' piccoli/grandi


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

# prompt molto buono se' la risposta ad una query e' distribuita in piu' pagine di pdf:
# Usa tutte le informazioni fornite nel contesto, anche se provengono
# da parti o pagine diverse del documento. Se la risposta richiede
# più sezioni, sintetizzale in un’unica spiegazione coerente.


def ask_question(user_namespace: str, question: str):
    # print('user_namespace ask_question here =', user_namespace)
    vectorstore = PineconeVectorStore(
        index=index,
        embedding=embeddings_model, 
        namespace=user_namespace, # the chunks related to each user (multitanent)
        text_key="text" # text e' dove e salvato i text chunks lato Pinecone
    )

    page_info = extract_page_info(question) # Vediamo se la query contiene riferimenti a delle pagine
    # tipo 'riassumi pagina 5', oppure 'riassumi da pagina 3 a 5'

     # ----------------------------------
    # CASO 1: Query con pagina specifica
    # ----------------------------------
    
    if page_info:

        if page_info[0] == "single":
            page_number = page_info[1]

            retriever = vectorstore.as_retriever(
                search_type="mmr",
                search_kwargs={
                    "k": 20,   
                    "fetch_k": 50, 
                    "lambda_mult": 0.8,
                    "filter":{
                         "page_start": {"$lte": page_number},
                         "page_end": {"$gte": page_number}
                        }
                }
            )

        elif page_info[0] == "range": # se uno user domanda 'riassumi da pagina 2 a 6'
            start_page = page_info[1]
            end_page = page_info[2]

            retriever = vectorstore.as_retriever(
                search_type="mmr",
                search_kwargs={
                    "k": 70, 
                    "fetch_k": 100,
                    "lambda_mult": 0.8,
                    "filter":{
                         "page_start": {"$lte": end_page},
                         "page_end": {"$gte": start_page}
                        }
                }
            )

    # ----------------------------------
    # CASO 2: Query semantica normale
    # ----------------------------------
    else: # qui si arriva se l'utente non specifica 'page' nella query('riassumi pagina 2'), ma fa' domande
        # specifiche tipo 'chi era enrico fermi?'

    # Qui facciamo solo 'partial' reranking(mmr), che e' una tecnica potente molto usata in produzione. 
    # Se avessimo bisogno del vero re-ranking vero, vedi nel branch "similarity-search-rank" come si fa'
    # ps In molti sistemi RAG moderni Non si usa threshold hard per reranking. Si usa solo top-k e poi si lascia decidere all’LLM
    # questo perche' Gli LLM sono molto bravi a ignorare chunk irrilevanti.
    # Quindi questa e' la soluzione piu' semplice e spesso migliore.
        retriever = vectorstore.as_retriever(
             search_type="mmr", # MMR = partial Reranking
             search_kwargs={ 
                 "k": 8, # 5-7 va bene. (Spesso 5 è più che sufficiente e riduce rumore.) ps. Gli LLM di default sono bravissimi ad ignorare chunks irrilevanti
                 # e ad attingere dalle info di soli 3 di questi, invece che da tutti e 8
                 # "filter": {"user_id": user_id}, 
                 "fetch_k": 15, 
                 "lambda_mult":0.8 # (0.5 per iniziare). 0.7/0.8 porta più peso alla similarità, 
                 # meno alla diversità e spesso migliora precisione.
            }
        ) 

    # Servirebbe threshold se:
    # hai migliaia di documenti, dominio misto, rumore elevato, vuoi ridurre token cost
    
    # docs_debugg = retriever.invoke(question)

    # print("\n--- CHUNKS RECUPERATI ---\n")
    # for i, d in enumerate(docs_debugg):
    #     print(f"\nChunk {i+1}")
    #     print("Page:", d.metadata.get("page"))
    #     print("Paragraph index:", d.metadata.get("paragraph_index"))
    #     print(d.page_content[:500])


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