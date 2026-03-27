from services.pdf_service import pdf_service
from config import DOCUMENTS_DIR

def test():
    docs = [d for d in DOCUMENTS_DIR.iterdir() if d.is_dir()]
    if not docs:
        print("No docs")
        return
        
    pdf_path = None
    for f in docs[0].iterdir():
        if f.suffix.lower() == ".pdf":
            pdf_path = f
            break
            
    if not pdf_path:
        return
        
    import fitz
    import pdfplumber
    with pdfplumber.open(str(pdf_path)) as pdf:
        page = pdf.pages[0]
        words = pdf_service._extract_words_smart_layout(page)
        
        text = " ".join(w['text'] for w in words)
        idx = text.find("In contrast")
        if idx != -1:
            print("FOUND AROUND 'In contrast':")
            print(text[idx-200:idx+500])
        else:
            print("'In contrast' not found!")

if __name__ == "__main__":
    test()
