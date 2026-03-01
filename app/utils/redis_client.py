import os
import redis
from dotenv import load_dotenv 
load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")

if REDIS_URL: # funziona quando deploiamo su redis
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
else: # funziona quando lavoriamo in locale, e dopo aver attivato docker(docker start my-redis)
    redis_client = redis.Redis( # redis setup. (fai docker run -d --name my-redis -p 6379:6379 redis) Spiegazione sotto
        host="localhost", # change when app is on render
        port=6379, # redis host. Questo e' il ponte di comunicazione tra questo localhost e il 'port' di redis
        # dentro il container docker
        decode_responses=True
    ) # il redis client (pip install redis) serve per definire la logica di redis tramite python. Mentre l'imagine/container
    # serve ad usare effettivamente l'app redis

#  quando deploy su render, redis_client diventa cosi':
#  REDIS_URL = os.getenv("REDIS_URL") la secret_key di redis
# redis_client = redis.from_url(REDIS_URL, decode_responses=True)