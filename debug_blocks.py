import fitz
from config import DOCUMENTS_DIR

def test():
    docs = [d for d in DOCUMENTS_DIR.iterdir() if d.is_dir()]
    pdf_path = next(f for f in docs[0].iterdir() if f.suffix.lower() == ".pdf")
    
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    blocks = page.get_text("blocks")
    
    for i, b in enumerate(blocks):
        # b: (x0, y0, x1, y1, text, block_n, block_type)
        if "emphasizes detailed processing" in b[4] or "CQ" in b[4]:
            print(f"--- Block {i} ---")
            print(f"bbox: {b[:4]}")
            print(f"text: {b[4][:100]}...")

if __name__ == "__main__":
    test()
