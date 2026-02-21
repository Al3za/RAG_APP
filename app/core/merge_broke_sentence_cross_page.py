# la function merge_broken_sentences controlla se la fine della pagina corrente finisce con un punto(.) 
# o un punto eclamativo(!) altrimenti capta i dati della pagina successiva, 
# in modo da fare un chunk cross page

# Unisce cross-page quando:

# la frase non è chiusa (. ! ? ; :)

# il testo successivo sembra continuazione naturale

# quindi evita chunk “monchi” come il tuo chunk 23

def merge_broken_sentences(chunks):
    merged = []
    i = 0
    MAX_MERGE_LEN = 900
    while i < len(chunks):
        current = chunks[i]

        if (
            merged
            and not merged[-1].page_content.strip().endswith((".", "!", "?", ":", ";")) # Guarda se l’ULTIMO CHUNK 
            # finisce con punteggiatura forte e se il next inizia con una maiuscola. In tal caso unisce questi chunk. Se non
            # MAX_MERGE_LEN questo chunk puo' diventare davvero grande. (Non importa se è fine pagina o è metà pagina)

            
            # es pagina 2-3.
            # tuttavia dobbiamo mettere un max_char anche qui, perche se sbadatamente uno studente creasse
            # un pdf dove ogni fine pagina non presenterebbe una punteggiatura, si creerebbero chunks grandissimi, e sarebbe un male per la
            # comparazione di ebeddings per che crea un potenziale merge tra chunks se questi embeddigs sono simili
            and current.page_content[:1].islower()
            and len(merged[-1].page_content) + len(current.page_content) <= MAX_MERGE_LEN
        ):
            merged[-1].page_content += " " + current.page_content

            # merged[-1].metadata["page_start"] = min(
            #   merged[-1].metadata.get("page_start", current.metadata["page_start"]),
            #   current.metadata.get("page_start")
            # )

            # merged[-1].metadata["page_end"] = max(
            #   merged[-1].metadata.get("page_end", current.metadata["page_end"]),
            #   current.metadata.get("page_end")
            # )

            # merged[-1].metadata["page_start"] = current.metadata.get("page_start")
            # merged[-1].metadata["page_end"] = current.metadata.get("page_end")
        else:
            merged.append(current)

        i += 1

    return merged
