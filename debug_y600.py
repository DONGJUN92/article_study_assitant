import fitz
from config import DOCUMENTS_DIR

def test():
    docs = [d for d in DOCUMENTS_DIR.iterdir() if d.is_dir()]
    pdf_path = next(f for f in docs[0].iterdir() if f.suffix.lower() == ".pdf")
    
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    words = page.get_text("words")
    
    print("WORDS Y > 600:")
    for w in words:
        if w[1] > 600:
             print(f"WORD: {w[4]:<15} | b: {w[5]:02} | x0: {w[0]:.2f} | y0: {w[1]:.2f}")

if __name__ == "__main__":
    test()
