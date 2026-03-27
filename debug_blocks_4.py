import fitz
from config import DOCUMENTS_DIR

def test():
    docs = [d for d in DOCUMENTS_DIR.iterdir() if d.is_dir()]
    pdf_path = next(f for f in docs[0].iterdir() if f.suffix.lower() == ".pdf")
    
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    words = page.get_text("words")
    
    for w in words:
        if "message" in w[4] or "content" in w[4] or "based" in w[4] or "cognitions" in w[4] or "CQ" in w[4]:
            if w[1] > 590:
                print(f"WORD: {w[4]:<15} | block_n: {w[5]} | y0: {w[1]:.2f}")

if __name__ == "__main__":
    test()
