import os
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from dotenv import load_dotenv 

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
If the answer cannot be determined from the context, say: "I don't know."

Context:
{context}

Question:
{question}
""")

# prompt molto buono se' la risposta ad una query e' distribuita in piu' pagine di pdf:
# Usa tutte le informazioni fornite nel contesto, anche se provengono
# da parti o pagine diverse del documento. Se la risposta richiede
# più sezioni, sintetizzale in un’unica spiegazione coerente.


def ask_question(user_id: str, question: str):
    print('user_id =', user_id)
    # 1️⃣ Vector store (index ESISTENTE)
    vectorstore = PineconeVectorStore(
        index=index, # pc.Index(index_name). l'indez Dove vengono salvati i dati(emb chunks) di ogni user
        embedding=embeddings_model, # per fare Retrieval (similarity search) tra query e embedded chunks in pinecone
        namespace=user_id, # fondamentale per trovare i chunks dello usare, e quindi avere corretto data retriving
        text_key="text" # text e' la key presente nel metadata degli embedded chunks in pinecone, dove risiedono i dati di ogni chunks
    )
    
    print(' =', user_id)

    retriever = vectorstore.as_retriever(
        search_kwargs={ # le prime quattro caselle con piu' alta similarita semantica con la query
            "k": 5 # solo una casella sono pochi dati, ma avendo le 4 piu' " semanticamente simili" alla query, lo llm definito sopra ci creera' una response piu' robuusta e' dettagliata, con i daty di "text" delle prime 4 caselle
            # "filter": {"user_id": user_id} # filtra tra i pdf chunks dello user specifico, altrimenti il modello leggerebbe gli pdf di tutti gli users
        }
    )

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