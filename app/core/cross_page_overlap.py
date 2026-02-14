# Crea overlap anche tra i chunk cross_page

CROSS_PAGE_OVERLAP = 50

def cross_page_overlap_def(clean_paragraph_docs):

    cross_page_overlap_chunk = []
    cross_page_overlap_chunk.append(clean_paragraph_docs[0]) # 
    for i in range(1, len(clean_paragraph_docs)):
        current_doc = clean_paragraph_docs[i] # il next chunk
        prev_doc = clean_paragraph_docs[i - 1] # il precedent chunk
    
        # Caso cross-page. Se per esempio page_start = 1 e page_end = 2
        if current_doc.metadata.get("page_start") != current_doc.metadata.get("page_end"):
    
            # Prendiamo gli ultimi 50 chars del precedente
            prefix = prev_doc.page_content[-CROSS_PAGE_OVERLAP:]
    
            # Evitiamo doppie duplicazioni
            if not current_doc.page_content.startswith(prefix):
                current_doc.page_content = prefix + " " + current_doc.page_content
                prev_doc.metadata["page_end"] = current_doc.metadata.get("page_end")
