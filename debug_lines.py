import fitz
from config import DOCUMENTS_DIR

def test():
    docs = [d for d in DOCUMENTS_DIR.iterdir() if d.is_dir()]
    pdf_path = next(f for f in docs[0].iterdir() if f.suffix.lower() == ".pdf")
    
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    words = page.get_text("words")
    
    b5_words = [w for w in words if w[5] == 5]
    
    line_dict = {}
    for w in b5_words:
        line_dict.setdefault(w[6], []).append(w)
        
    for l_num in sorted(line_dict.keys())[:10]: # Print first 10 lines
        line_words = line_dict[l_num]
        line_words.sort(key=lambda w: w[7]) # sort by word_n
        text = " ".join(w[4] for w in line_words)
        print(f"Line {l_num}: {text[:80]}")

if __name__ == "__main__":
    test()
