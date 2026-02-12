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

    while i < len(chunks):
        current = chunks[i]

        if (
            merged
            and not merged[-1].page_content.strip().endswith((".", "!", "?", ":", ";"))
            and current.page_content[:1].islower()
        ):
            merged[-1].page_content += " " + current.page_content

            merged[-1].metadata["page_start"] = min(
              merged[-1].metadata.get("page_start", current.metadata["page_start"]),
              current.metadata.get("page_start")
            )

            merged[-1].metadata["page_end"] = max(
              merged[-1].metadata.get("page_end", current.metadata["page_end"]),
              current.metadata.get("page_end")
            )

            # merged[-1].metadata["page_start"] = current.metadata.get("page_start")
            # merged[-1].metadata["page_end"] = current.metadata.get("page_end")
        else:
            merged.append(current)

        i += 1

    return merged
