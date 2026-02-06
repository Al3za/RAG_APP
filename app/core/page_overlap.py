# page overlap fa parte del processo di  PDF-aware chunkingdella funzione "ingest_pdf".

# questa funzione fa' si che se un paragrafo si estande da una pagina all'altra(da pagina 3 a 4), allora il evitiamo una
# rottura del chunk dovuta al metodo PyPDFLoader, che trancia tutti i chunks di ogni pagina, e non 
# perette overlap (150) se un chunk si estende da una pagina all-altra. 
# quesata funzione serve a prevenire cio, quindi se un paragrafo inizia alla fine della pagina 3 del pdf, fino alla pagina 4,
# non si spezza la semanticita grazie al page overlap che andremo ad eseguire nella funzione sotto.
# semplicemente diciamo al programma di unire pagina 1 e 2, 2e 3, 3 e 4... cosi che i chunks siano  
# un blocco unico nell'eventualita che una parameter chunk si estende da una pagina ad un altra
# questo lo facciamo per aumentera ulteriormente la semanticita dei chunks

# PS ci sono anche altri 2 approcci comunemente usati per fare cio:
#  1) Ricostruzione paragrafo cross-page → solo se vuoi massima precisione
# 2) unstructured / GROBID → quando vuoi riconoscere sezioni automaticamente
# Per ora: questa che stiamo usando e' la soluzione giusta (usata anche in prod 💪)

from langchain_core.documents import Document

def build_page_windows(docs, window_size=2): # window_size e' solo un parametro che definisce un num, niente a che fare con windows o chrome
    page_windows = []

    for i in range(len(docs)):
        window_docs = docs[i:i + window_size] # uniamo i docs(le pagine del pdf): i=0 ->[pagina0,pagina1],
    #  i	      docs[i:i+2]        # window_size non ha conoscenza del PDF, e solo il nr
    #  0	    docs[0], docs[1]     # che aiuta a fare slicing di lista dei dati docs
    #  1	    docs[1], docs[2]
    #  2	    docs[2], docs[3]
        
        # Unione del testo. Qui concateni il testo delle due pagine mantenendo separazione naturale
        # (page_content=(text della pagina_0)), page_content=(text della pagina_1)....
        combined_text = "\n\n".join(d.page_content for d in window_docs) # [testo pagina 3], [testo pagina4]

        # Metadata nuova (chiave!)
        # qui stai creando metadata di finestra, non di pagina singola.
        # quindi se questo chunk copre più pagine, lo vediamo chiaramente nel metadata qui.
        # Il metadata e' importantissimo per il corretto funzionamento del rag, e dentro di esso devono 
        # e importante che sia descritto dove "si trovano i dati"
        metadata = { # in window_docs (che contiene i dati docs), abbiamo questi dati  metadata={"page": 0,txt:...}
            # ed e' cosi' che sappiamo il nr della pagina
            "page_start": window_docs[0].metadata.get("page"),
            "page_end": window_docs[-1].metadata.get("page"),
            "source": window_docs[0].metadata.get("source"),
        }
        
        # Output della funzione. qui appendiamo questi dati in page_windows e ritorniamo.
        page_windows.append(
            Document(page_content=combined_text, metadata=metadata)
        )

    return page_windows
