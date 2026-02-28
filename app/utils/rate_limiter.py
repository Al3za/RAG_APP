from app.utils.redis_client import redis_client
from fastapi import HTTPException


MAX_REQUESTS = 15
WINDOW_SECONDS = 60


def rate_limit(namespace: str):
    key = f"rate_limit:{namespace}"

    current = redis_client.incr(key)

    if current == 1:
        redis_client.expire(key, WINDOW_SECONDS)

    if current > MAX_REQUESTS:
        print('Too many requests rate limit')
        raise HTTPException(
            status_code=429,
            detail="Too many requests"
        ) # code stops here
    
    # DURANTE LO SVILUPPO IN LOCALE DOBBIAMO USARE UNA VM. IO HO USATO DOCKER:
    # docker run -d --name my-redis -p 6379:6379 redis. 
    # Questo codice fa':
    # 1) Prende l'ultima imagine di redis(... 6379 "redis") da docker hub, 
    # 2) Usiamo questa imagine nel nostro container che ho chiamato "my-redis". 
    # Ora abbiamo una light weight Redis app sul nostro container.
    # Usiamo il port 6379 per comunicare con redis. Perche redis e' ora sul nostro Vm container, ma
    # Per comunicare con essa dobbiamo usare il port specifico suo, che e' il port nr 6379. 
    # Un po' come un frontend che usa un endpoint per ottenere risorse da un backend server.

    # siccome abbiamo redis_client = host="localhost", port=6379, il comando di docker "-p 6379:6379" mette in comunicazion
    # il nostro localhost con 'l endpoint' di redis dentro il nostro docker container
    
    # ps redis (.... -p 6379:6379 redis) è il nome(id) dell’immagine del Docker Hub 
    
    # docker stop my-redis # partire il container che contiene redis
    # docker start my-redis # fermare il container

def ingest_status(namespace: str, status:str): # SET status to let the client know when the pdf is 
    # ingested and inserted on s3 and pinecone
        redis_client.set(f"doc_status:{namespace}", # no return needed here
                         status,
                         ex=600) # 10 min, Così non rimane sporco per sempre.

def get_ingest_status(namespace: str): # GET status to let the client know when the pdf is 
    # ingested and inserted on s3 and pinecone
       return redis_client.get(f"doc_status:{namespace}") # return needed