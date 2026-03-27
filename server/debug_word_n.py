import fitz
from config import DOCUMENTS_DIR

def test():
    docs = [d for d in DOCUMENTS_DIR.iterdir() if d.is_dir()]
    pdf_path = next(f for f in docs[0].iterdir() if f.suffix.lower() == ".pdf")
    
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    words = page.get_text("words")
    
    print("WORDS IN BOTTOM HALF:")
    for w in words:
        if w[1] > 590:
            if w[4] in ['emphasizes', 'detailed', 'processing', 'of', 'CQ', 'd', 'fa', 'based', 'cognitions', 'in', 'mediating', 'opinion', 'change,']:
                print(f"'{w[4]}': b={w[5]:02} l={w[6]:02} w={w[7]:02} | x0={w[0]:.1f}")

if __name__ == "__main__":
    test()
