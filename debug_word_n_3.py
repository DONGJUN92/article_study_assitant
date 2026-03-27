import fitz
from config import DOCUMENTS_DIR

def test():
    docs = [d for d in DOCUMENTS_DIR.iterdir() if d.is_dir()]
    pdf_path = next(f for f in docs[0].iterdir() if f.suffix.lower() == ".pdf")
    
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    words = page.get_text("words")
    
    # Target phrase: "emphasizes detailed processing"
    target_y = None
    for i, w in enumerate(words):
        if w[4] == 'detailed' and words[i-1][4] == 'emphasizes':
            target_y = w[1]
            break
            
    if target_y:
        print(f"FOUND TARGET at y={target_y}")
        print("\n--- ALL WORDS NEAR TARGET Y (y +/- 10) ---")
        near_words = [w for w in words if abs(w[1] - target_y) < 10 or 'CQ' in w[4] or 'fa' in w[4]]
        near_words.sort(key=lambda w: (w[5], w[6], w[7])) # Sort by fitz block, line, word
        
        for w in near_words:
            print(f"'{w[4]}': b={w[5]:02} l={w[6]:02} w={w[7]:02} | x0={w[0]:.1f}")

if __name__ == "__main__":
    test()
