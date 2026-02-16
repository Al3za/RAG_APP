from langchain_core.documents import Document
# Unire i paragraph troppo piccoli (super-pulito ✨) 

# in pre_merge_small_paragraphs:
# facciamo merge di chunks < 130 char perche gli embeddings di questi piccoli chunks possono causare imprecisione, e portano
# il modello a confondersi, risultando in un possibile bad retrival

# ✔ Unisce small tra loro
# ✔ Unisce smal chunks al precedente o prossimo chiunk al patto di non creare un chunk > 600 char
# altrimenti unisce i chunks tra loro(tutto ✅ Solo se stessa pagina)
# Unisce small al precedente grande

# Solo stessa pagina

# Mantiene max 600

# Non crea incoerenze

from langchain_core.documents import Document

def pre_merge_small_paragraphs(
    paragraph_docs,
    min_chars=130,
    max_chars=600
):
    if not paragraph_docs:
        return paragraph_docs

    merged = []

    for doc in paragraph_docs:
        text = doc.page_content
        text_len = len(text)
        page = doc.metadata.get("page_start")

        # 🔹 Caso 1: chunk piccolo
        if text_len < min_chars:
            print('pre_merge_small_paragraphs hit')
            print('small text to merge =', doc.page_content)
            if merged:
                prev_doc = merged[-1]
                prev_len = len(prev_doc.page_content)
                prev_page = prev_doc.metadata.get("page_start")

                # ✅ stessa pagina + non supera max_chars
                if prev_page == page and (prev_len + 1 + text_len) <= max_chars:
                    prev_doc.page_content += " " + text

                    # aggiorniamo eventuale page_end se serve
                    prev_doc.metadata["page_end"] = doc.metadata.get("page_end")
                    continue

            # ❌ non possiamo unirlo → lo aggiungiamo separato
            merged.append(doc)

        # 🔹 Caso 2: chunk normale/grande
        else:
            merged.append(doc)

    return merged




# Qui uniamo i semantics chunks che sono < 250 char. Li uniamo chunk appena precedente se questo non supera il max_char = 1200. Se
# Il chunk che doveva essere unito e' gia troppo grande, proveremo ad unirlo con il diretto prossimo chunk. se anche questo fosse
# gia troppo grande, allora il merge non avviene, e questo chunk viene lasciato alla grandezza che aveva (< 250 char).
 # Questo puo' avvienire alla fine del pdf, quando eventuali paragraph piccoli vengono uniti tra loro, ma essendo comunque piccoli
# (120 char ognuno) andranno a formare un chunk di soli 240 char. questo parag congiunto , se non viene 'merged' con un altro
# nella fun semantic_chunk_paragraphs perche non similarmente semantico o perche sfora i 1200 char, si ritrova solo con la grandezza
# iniziale di 240 char, il che e' troppo piccolo, perche gli embeddings di chunks < 250 char possono causare imprecisione, e portano
# il modello a confondersi, risultando in un possibile bad retrival


def post_merge_semantic_small_chunks(
    chunks,
    min_chars=250,
    max_chars=1200
):
    if not chunks:
        return chunks

    merged = []
    i = 0

    while i < len(chunks):
        current = chunks[i]
        current_len = len(current.page_content)

        # Se chunk abbastanza grande → mantieni
        if current_len >= min_chars:
            merged.append(current)
            i += 1
            continue

        # Se ultimo elemento → mantieni
        if i + 1 >= len(chunks):
            merged.append(current)
            break

        next_chunk = chunks[i + 1]
        combined_len = current_len + len(next_chunk.page_content)

        if combined_len <= max_chars:
            new_text = current.page_content + " " + next_chunk.page_content
            new_meta = current.metadata.copy()

            merged.append(
                Document(page_content=new_text, metadata=new_meta)
            )

            i += 2  # salta esplicitamente entrambi. Qui diciamo  “NON fare merge a catena” — cosa significa davvero: 
            # Questo evita di concatenare piu' small chunks. Solo 1 chunk < 250 char si puo' concatenare al precedente o al prossimo. 
            # E consigliato concatenare massimo uno perche' se avessimo tanti piccoli chunks che si andrebbero a concatenare, si potrebbe 
            # perdere semanticita', perche' ci sarebbe il rischio che stessimo mescolando informazioni di diversi chunk tra loro.
            # per questo e' anche importante che ogni piccolo chunk sia unito solo con il chunk appena precedente o quello subito dopo, 
            # questo perche' essendo vicini e' piu' probabile che questi condividano informazioni simili
        else:
            merged.append(current)
            i += 1

    return merged


# def post_merge_semantic_small_chunks( # Con il mio setup attuale (base chunk: 450 chars e pre-merge <130 chars)   Nel 90–95% dei casi questa funzione
#         # non verra mai invocata
#     chunks,# i cleaned chunks, pre merged
#     min_chars=250, # sweet spot di default, per mergare i semantic chunks di questa grandezza 
#     max_chars=1200 # numero massimo di chars per semantic_chunks. Oltre, gli embeddings creati perderebbero di precisione e verrebbero
#     # annacquati da dati non rilevanti
# ):
#     if not chunks:
#         return chunks

#     merged = []
#     skip_next = False

#     for i, chunk in enumerate(chunks):
#         if skip_next:
#             skip_next = False
#             continue

#         chunk_len = len(chunk.page_content)

#         if chunk_len >= min_chars:
#             merged.append(chunk)
#             continue

#         # prova a unire al successivo (preferito)
#         if i + 1 < len(chunks):
#             next_chunk = chunks[i + 1]
#             combined_len = chunk_len + len(next_chunk.page_content)

#             if combined_len <= max_chars:
#                 new_text = chunk.page_content + " " + next_chunk.page_content
#                 new_meta = chunk.metadata.copy()

#                 merged.append(
#                     Document(page_content=new_text, metadata=new_meta)
#                 )
#                 skip_next = True # “NON fare merge a catena” — cosa significa davvero. 
#                 # Questo evita di concatenare piu' small chunks. Solo 1 chunk < 250 char si puo' concatenare al precedente o al prossimo. 
#                 # E consigliato concatenare massimo uno perche' se avessimo tanti piccoli chunks che si andrebbero a concatenare, si potrebbe 
#                 # perdere semanticita', perche' ci sarebbe il rischio che stessimo mescolando informazioni di diversi chunk tra loro.
#                 # per questo e' anche importante che ogni piccolo chunk sia unito solo con il chunk appena precedente o quello subito dopo, 
#                 # questo perche' essendo vicini e' piu' probabile che questi condividano informazioni simili.
#                 continue

#         # fallback: resta solo
#         merged.append(chunk)

#     return merged

