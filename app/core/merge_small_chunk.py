# Unire i chunk troppo piccoli (super-pulito ✨) 

# Se nel caso in una pagina abbiamo 1700 caratteri, e il chunk size = 800 come nel nostro caso, 
# allora si creano 2 full size chunk di 800 caratteri, e uno davvero piccolo, di 250(150 di overlapp + i 100 rimasti)
# questi chunk contengono troppo poche informazioni per essere rilevanti, ma invece di scartarli
# se sono piu' piccoli di un certo nr (ad esempio 200), li inseriamo nel chunk precedente, cosi si mantiene
# piu' semantica nel chunk e si evitano inutili piccoli chucks

def merge_small_chunks(chunks, min_size=250):
    if not chunks:
        return chunks

    merged = [chunks[0]]

    for chunk in chunks[1:]:
        if len(chunk.page_content) < min_size:
            merged[-1].page_content += " " + chunk.page_content
        else:
            merged.append(chunk)

    return merged
