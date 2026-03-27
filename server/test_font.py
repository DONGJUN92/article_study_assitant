import pdfplumber
import fitz
from config import DOCUMENTS_DIR

def test():
    docs = [d for d in DOCUMENTS_DIR.iterdir() if d.is_dir()]
    pdf_path = next(f for f in docs[0].iterdir() if f.suffix.lower() == ".pdf")
    
    print("--- pdfplumber extraction ---")
    with pdfplumber.open(str(pdf_path)) as pdf:
        page = pdf.pages[0]
        words = page.extract_words(keep_blank_chars=False)
        garb = [w['text'] for w in words if "CQ" in w['text'] or "fa" in w['text']]
        print("pdfplumber extracted:", garb)
        
    print("\n--- fitz (PyMuPDF) extraction ---")
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    words = page.get_text("words")
    # find words around the same Y coordinate (bottom of page 1)
    # The bottom of page 1 Y is roughly 600-750.
    bottom_words = [w[4] for w in words if w[1] > 600]
    text = " ".join(bottom_words)
    idx = text.find("emphasizes detailed processing of")
    if idx != -1:
        print("Found in fitz:", text[idx:idx+200])

if __name__ == "__main__":
    test()
