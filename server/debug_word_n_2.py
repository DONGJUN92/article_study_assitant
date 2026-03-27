import fitz
from config import DOCUMENTS_DIR

def test():
    docs = [d for d in DOCUMENTS_DIR.iterdir() if d.is_dir()]
    pdf_path = next(f for f in docs[0].iterdir() if f.suffix.lower() == ".pdf")
    
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    words = page.get_text("words")
    
    # Let's locate the sentence "systematic view of persuasion emphasizes"
    target_y = None
    for w in words:
        if w[4] == 'persuasion':
            target_y = w[1]
            print(f"FOUND 'persuasion' at y={target_y}")
            break
            
    if target_y:
        print("\n--- ALL WORDS NEAR TARGET Y ---")
        near_words = [w for w in words if abs(w[1] - target_y) < 30]
        near_words.sort(key=lambda w: (w[5], w[6], w[7])) # Sort by fitz block, line, word
        
        for w in near_words:
            print(f"'{w[4]}': b={w[5]:02} l={w[6]:02} w={w[7]:02} | x0={w[0]:.1f}")

if __name__ == "__main__":
    test()
