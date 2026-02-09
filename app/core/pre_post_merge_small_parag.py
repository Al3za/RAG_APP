from langchain_core.documents import Document
# Unire i paragraph troppo piccoli (super-pulito ✨) 

# facciao merge di chunks < 130 char perche gli embeddings di questi piccoli chunks possono causare imprecisione, e portano
# il modello a confondersi, risultando in un possibile bad retrival


def pre_merge_small_paragraphs(paragraph_docs, 
                               min_chars=130,
                               max_chars=600):
    if not paragraph_docs:
        return paragraph_docs

    merged = []
    buffer = None

    for doc in paragraph_docs: # paragraph_docs = the cleaned paragraf extracted from each pdf page (window 2)

        text_len = len(doc.page_content) # lunghezza dei char di ogni paragrafo
        
        if text_len < min_chars:
            if buffer is None:
                buffer = doc # doc = paragraph
            else:
                # evita chunk gigante nel caso chi fossero ad esempio 10 paragrafi < 130 char. qui evitiamo questa grande concatenazione,
                # creando un unione di paragrafi per un massimo di 600 char. I paragrafi overflowed andranno a creare un nuovo chunk
                # sempre con questo limite massimo, e senza perdere semanticita'.
                if len(buffer.page_content) + text_len <= max_chars:
                   buffer.page_content += " " + doc.page_content
                else:
                    merged.append(buffer)
                    buffer = doc
        
        else:
            if buffer is not None:
                # buffer.page_content += " " + doc.page_content
                merged.append(buffer)
                buffer = None
            merged.append(doc)    

    if buffer is not None:
        merged.append(buffer)

    return merged



# Qui uniamo i semantics chunks che sono < 250 char. Li uniamo chunk appena precedente se questo non supera il max_char = 1200. Se
# Il chunk che doveva essere unito e' gia troppo grande, proveremo ad unirlo con il diretto prossimo chunk. se anche questo fosse
# gia troppo grande, allora il merge non avviene, e questo chunk viene lasciato alla grandezza che aveva (< 250 char).
 # Questo puo' avvienire alla fine del pdf, quando eventuali paragraph piccoli vengono uniti tra loro, ma essendo comunque piccoli
# (120 char ognuno) andranno a formare un chunk di soli 240 char. questo parag congiunto , se non viene 'merged' con un altro
# nella fun semantic_chunk_paragraphs perche non similarmente semantico o perche sfora i 1200 char, si ritrova solo con la grandezza
# iniziale di 240 char, il che e' troppo piccolo, perche gli embeddings di chunks < 250 char possono causare imprecisione, e portano
# il modello a confondersi, risultando in un possibile bad retrival

def post_merge_small_chunks( # Con il mio setup attuale (base chunk: 450 chars e pre-merge <130 chars)   Nel 90–95% dei casi questa funzione
        # non verra mai invocata
    chunks,# i cleaned chunks, pre merged
    min_chars=250, # sweet spot di default, per mergare i semantic chunks di questa grandezza 
    max_chars=1200 # numero massimo di chars per semantic_chunks. Oltre, gli embeddings creati perderebbero di precisione e verrebbero
    # annacquati da dati non rilevanti
):
    if not chunks:
        return chunks

    merged = []
    skip_next = False

    for i, chunk in enumerate(chunks):
        if skip_next:
            skip_next = False
            continue

        chunk_len = len(chunk.page_content)

        if chunk_len >= min_chars:
            merged.append(chunk)
            continue

        # prova a unire al successivo (preferito)
        if i + 1 < len(chunks):
            next_chunk = chunks[i + 1]
            combined_len = chunk_len + len(next_chunk.page_content)

            if combined_len <= max_chars:
                new_text = chunk.page_content + " " + next_chunk.page_content
                new_meta = chunk.metadata.copy()

                merged.append(
                    Document(page_content=new_text, metadata=new_meta)
                )
                skip_next = True # “NON fare merge a catena” — cosa significa davvero. 
                # Questo evita di concatenare piu' small chunks. Solo 1 chunk < 250 char si puo' concatenare al precedente o al prossimo. 
                # E consigliato concatenare massimo uno perche se avessimo tanti piccoli chunks che si andrebbero a concatenare, si potrebbe 
                # perdere semanticita', perche' ci sarebbe il rischio che stessimo mescolando informazioni diverse tra loro.
                # per questo e' anche importante che ogni piccolo chunk sia unito con il chunk  precedente o quello subito dopo, 
                # questo perche essendo vicini e' piu' probabile che questi condividano informazioni simili
                continue

        # fallback: resta solo
        merged.append(chunk)

    return merged
