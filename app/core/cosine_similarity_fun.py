import numpy as np
from langchain_core.documents import Document

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calcola la similarità coseno tra due embedding"""
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))



def semantic_chunk_paragraphs(paragraph_docs, 
                              embeddings_model, 
                              sim_threshold=0.65,
                              max_chars=1200):    # ≈ 200 tokens: limite consigliato per embeddings 
                            #   affidabili e precisi. Se superiori, risultano annacquati
    """
    paragraph_docs: lista in formato "Document"(con dati testo e metadata) dei un paragrafi che abbiamo creato nel file ingest.py
    embeddings_model: modello OpenAIEmbeddings
    sim_threshold: soglia cosine similarity per unire paragrafi (0.8 e consigliabile, ma la puoi
    customizzare come vuoi)
    """
    if not paragraph_docs:
        return []
    # 🔹 Pre-compute embeddings per paragrafo (rate-limit friendly). serve per trasformare i paragrafi
    # definiti in paragraph_docs in embeddings per poterlipassare alla funzione cosine_similarity, 
    # che misura la similarita' tra gli embeddings. se i paragrafi sono simili, questi vengono agregati, fino ad un limite(max_chars) di 1200 char.
    # Il limite serve per non avere chunks non superiori a 1200 char, che comporterebbero embeddings
    # troppo grandi che risulterebbero in embeddings poco precisi e rumorosi per il modello
    # Lo sweetspot per gli embeddings e di 200 tokens (piu o meno 1200 char per l'appunto)
    paragraph_embeddings = [
        np.array(embeddings_model.embed_query(doc.page_content))
        for doc in paragraph_docs
    ] # ricaviamo un array contenente gli embeddings di tutti i chunks. Coordinate degli embeddings
    # necessarie per attingere(da dentro il loop sotto), ai corretti emb di ogni chunk
    # print('paragraph_embeddings len =', len(paragraph_embeddings)) # la logica del semantic chunking puo separe
    # i chunks 'merged' in 'post_merge_small_chunks' se questi non similarmente semantici.
    # inoltre. se un grande 'pre'semantic chunk document arriva qui, questo viene spezzettato in chunk
    # in piu' chunks, oppure unisce 2 o 3 chunks fortemante simili semanticamente, senza mai sforare 
    # il max_char = 1200 (piu' di 1200)
    final_chunks = []

    # Inizializzazione del primo chunk. Questo e' il primo chunk di riferimento semantico, e ci serve come
    # riferimento per per poter costruire un eventuale paragrafo più grande 
    current_chunk_text = paragraph_docs[0].page_content # il text data del paragrafo. (cambia dentro il loop)
    current_meta = dict(paragraph_docs[0].metadata) # il  dict dei metadati del paragrafo 
    current_meta["paragraph_end_index"] = current_meta["paragraph_index"] # (cambia dentro il loop)
    current_meta["page_start"] = current_meta["page_start"] 
    current_meta["page_end"] = current_meta["page_end"] # (cambia dentro il loop)
    

     # embedding del chunk aggregato (inizialmente = primo paragrafo)
    current_embedding = paragraph_embeddings[0] # l'embedding iniziale. (cambia nel loop)
    # print('paragraph_docs for semantic chunking =', paragraph_docs)
    
    # Loop principale (il cuore della funzione).
    # Qui Iteri sui chunk successivi uno a uno
    for i in range(1, len(paragraph_docs)): # passiamo questi dati di 
        # Per ogni chunk, decidi se fonderlo col corrente o chiudere il chunk corrente.
        # ricorda che il primo chunk sopra e' il riferimento iniziale che avvia cio'
        next_text = paragraph_docs[i].page_content
        next_embedding = paragraph_embeddings[i] # confrontato nella funzione cosine con quello precedente(current_embedding), o con i chunk "merged" precedenti

        # 🔹 similarità: CHUNK AGGREGATO vs PARAGRAFO
        # in caso 3 o piu' chunks sono simili semanticamente, confronti i merged chunks(A+B) con il
        # chunk  C
        # al primo turn del loop, confrontiamo l'embeddings del primo emb chunk con il secondo
        # emb chunk, ricavato dall'array di emb chunks definito in paragraph_embeddings[i]
        sim = cosine_similarity(current_embedding, next_embedding)  # aggiornato continuamente ad ogni turn del loop, e cambia diversamente in base se i chunks
        # print(f"SIM {i-1}->{i}: {sim:.3f}") # guarda la forza in % della similarita' semantica

        #  sono "stati uniti" o meno. Se sono stati uniti i chunks allora "current_embedding"
        # aggiornato e' uguale risultera all'unione di questi embeddings diviso diviso 2.
        # E quindi il loop procede e sempre nella funzione cosine_similarity calcoleremo la similarita' 
        # semantica tra l'unione di questi embeddings, e il prossimo emb chunk. dato che gli 
        # embeddings sono su chunks di grandezza media 450 char, di solito questi "emb chunks uniti" 
        # equivalgono all'unione di 2-3 chunks, prima di venire limitati dal paramatro max_char, 
        # che limita la grandezza di questi chunks a max 1200 char (descrizione dettagliata a fine file).
         
        # Nel caso il primo emb chunk non avesse nessuna similarita' semantica con il "next" emb chunk,
        # restera' il chunk che era definito in "current_embedding" , e "current_embedding" diventera
        # uguale al "next_embedding"
        # e' cosi' via per tutta la durata del loop

        # 🔹 controllo dimensione. calcoli quanto diventerebbe grande il chunk prima di unirlo
        # evitare embedding > 200 tokens (per token piu' precisi e meno rumorosi, annacquati)

      
        merged_size = len(current_chunk_text) + 1 + len(next_text)

         # Decisione di merge (la regola d’oro). al primo turn del loop come abbiamo detto verifichiamo
        # riportiamo quanti di questi chunks hanno una similarita semantica >= 0.8 al primo emb chunk 
        if sim >= sim_threshold and merged_size <= max_chars:
             # ✅ merge consentito tra i chunks con similarta' >= 0.8 e totale lungezza di 1200 char
            # aggiorniamo current_chunk_text e metadata
            current_chunk_text += " " + paragraph_docs[i].page_content # merge chunks
            current_meta["paragraph_end_index"] = paragraph_docs[i].metadata["paragraph_index"]
            current_meta["page_start"] = min(current_meta["page_start"], paragraph_docs[i].metadata["page_start"])
            current_meta["page_end"] = max(current_meta["page_end"], paragraph_docs[i].metadata["page_end"])

            # current_meta["page_end"] = paragraph_docs[i].metadata["page_end"] 
       
            # questa soluzione va bene per iniziare, poi se e' necessario passiamo all soluzione 
            # sotto. (leggi a cosa serve nella desc di current_embedding appena sotto)
            current_embedding = (
                current_embedding + next_embedding
            ) / 2.0  # Dividiamo per 2 perché stiamo mediando due entità semantiche. Dopo un merge, (A+B) diventa una sola entità
            
            # 🔹 tieni traccia del peso. Questi dati ci servono per creare un nuovo current_embedding piu' preciso e pesato
            #  in base hai chunks che abbiamo "merged"
            # piu' questo nuovo merged chunk e' "preciso', piu' "precisamente" la funzione cosine_similarity trovera 
            # un embedding della lista semanticamente simile a questo "merged" embedding 

            # current_weight = len(current_chunk_text)
            # next_weight = len(next_text)

            # # 🔹 aggiorna embedding aggregato (media vettoriale)
            # current_embedding = (
            #     current_embedding * current_weight +
            #     next_embedding * next_weight
            # ) / (current_weight + next_weight)
           

        else:
            # ❌ chiudi chunk corrente. se lo emb chunk non ha nessuna similarita semantica con il next
            # emb chunk, o se l'unione dei chunks supera i 1200 char, allora salviamo il 'merged' chunk
            # definito in if...:
            final_chunks.append( # appendiamo i nuovi chunks (merged e non merged) uno alla voltanel final_chunks array
                Document(page_content=current_chunk_text, 
                         metadata=current_meta)
            )
            
            current_chunk_text = next_text
            current_meta = dict(paragraph_docs[i].metadata)
            current_meta["paragraph_end_index"] = paragraph_docs[i].metadata["paragraph_index"]
            current_meta["page_start"] = min(current_meta["page_start"], paragraph_docs[i].metadata["page_start"])
            current_meta["page_end"] = max(current_meta["page_end"], paragraph_docs[i].metadata["page_end"])# (cambia dentro il loop)
            current_embedding = next_embedding # next emb sara comparato con next_next emb per vedere se c e similarita 

    # aggiungi ultimo chunk.
    # qui arriviamo in caso gli ultimi chunks siano semanticamente simile, e salviamo questi chunks
    # a fine loop
    final_chunks.append(Document(page_content=current_chunk_text, metadata=current_meta))
    return final_chunks # qui ritorniamo un array contenente piu' chunk semanticamente simili, e
    # chunks normali  


# COSA AVVIENE QUI? (production standard)
# Abbiamo definito "max_char" = 1200. Se capita che  5 chunks (chunk a,b,c,d,e) sono semanticamente simili(>=0.8) 
# e ognuno circa da 500 chars di grandezza, il merge descritta nell mia fuzione sopra avviene cosi':
# la prima coppia di chunks viene unita tra loro a formare il primo chunck unito(chunk a+b). 
# il Chunck C risulta 'overflow' perche il chunk a+b e gia di cinra 1000 char, e quindi al chunk C non viene
# permesso il merge a causa sel max_char limit.
# Quindi come in precedenza, C verra paragonato con il il chunk D e' questi verranno "merged" 
# formando un nuovo chunk unito (chunk c+d), proprio come il primo.
# Quindi seguendo questa logica,il chunk (E) risulta overflowed e resta da solo, restando il chanck come era.

# Comportamento corretto (production-grade)

# Il merge dovrebbe essere:

# A (500)

# A+B (1000) ✅

# A+B+C (1500) ❌ overflow

# 👉 chiudi A+B
# 👉 inizi nuovo chunk con C

# Poi:
# 4. C+D (1000) ✅
# 5. C+D+E (1500) ❌ overflow

# 👉 chiudi C+D
# 👉 E resta da solo