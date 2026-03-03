## capiamo se lo user ha scritto una query che fa' riferimento ad una pagina (es a pagina 2, da pagina 2 a 4, o solo 2, o 2-4)
# (sia in inglese che in italiano)
import re

def extract_page_info(question: str):
    """
    Estrae informazioni di pagina dalla query.
    Supporta:
    - Italiano: 'pagina 3', 'da pagina 2 a 4', 'pag. 5-7'
    - Inglese: 'page 2', 'from page 2 to 5', 'page 3-5'
    
    Ritorna:
    - ("single", page_number) per singola pagina
    - ("range", start_page, end_page) per range
    - None se non trova info
    """
    question = question.lower()

    # Italiano
    range_match_it = re.search(
        r'pag(?:ina|ine|\.?)?\s*(\d+)\s*(?:-|a|alla|fino a)\s*(\d+)', question
    )
    single_match_it = re.search(
        r'pag(?:ina|ine|\.?)?\s*(\d+)', question
    )

    # Inglese
    range_match_en = re.search(
        r'(?:from\s+)?page\s*(\d+)\s*(?:-|to)\s*(\d+)', question
    )
    single_match_en = re.search(
        r'page\s*(\d+)', question
    )

    # Priorità: range prima di single
    if range_match_it:
        return ("range", int(range_match_it.group(1)), int(range_match_it.group(2)))
    elif single_match_it:
        return ("single", int(single_match_it.group(1)))
    elif range_match_en:
        return ("range", int(range_match_en.group(1)), int(range_match_en.group(2)))
    elif single_match_en:
        return ("single", int(single_match_en.group(1)))
    
    return None