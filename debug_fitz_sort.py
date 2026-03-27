import fitz
from config import DOCUMENTS_DIR

def test():
    docs = [d for d in DOCUMENTS_DIR.iterdir() if d.is_dir()]
    pdf_path = next(f for f in docs[0].iterdir() if f.suffix.lower() == ".pdf")
    
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    
    # fitz words: (x0, y0, x1, y1, text, block_n, line_n, word_n)
    words = page.get_text("words")
    
    # Sort natively by block, then line, then word
    words.sort(key=lambda w: (w[5], w[6], w[7]))
    
    # Let's reconstruct the text and see if "message content" is preserved
    text = " ".join(w[4] for w in words)
    
    idx = text.find("emphasizes detailed processing of")
    if idx != -1:
        print("RESULT:")
        print(text[idx:idx+250])
        
    print("\nDid 'CQ' get interleaved?")
    print("CQ in text?", "CQ d fa" in text)
    
if __name__ == "__main__":
    test()
