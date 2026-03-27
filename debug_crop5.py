import pdfplumber
from services.pdf_service import pdf_service
from config import DOCUMENTS_DIR
from collections import Counter

def find_gutter(words, page_width):
    # Find most common right-edges (x1) in the middle 30-50% of page
    center_start = page_width * 0.35
    center_mid = page_width * 0.50
    center_end = page_width * 0.65
    
    # Left column right edges
    left_x1s = [round(w['x1']) for w in words if center_start < w['x1'] < center_mid + 20]
    # Right column left edges
    right_x0s = [round(w['x0']) for w in words if center_mid - 20 < w['x0'] < center_end]
    
    if not left_x1s or not right_x0s:
        return page_width / 2.0
        
    c_left = Counter(left_x1s)
    c_right = Counter(right_x0s)
    
    # Most common edges
    best_left_x1 = c_left.most_common(1)[0][0]
    best_right_x0 = c_right.most_common(1)[0][0]
    
    gutter_center = (best_left_x1 + best_right_x0) / 2.0
    print(f"Best Left col edge: {best_left_x1}")
    print(f"Best Right col edge: {best_right_x0}")
    print(f"Calculated Gutter Center: {gutter_center}")
    return gutter_center

def test():
    docs = [d for d in DOCUMENTS_DIR.iterdir() if d.is_dir()]
    pdf_path = None
    for f in docs[0].iterdir():
        if f.suffix.lower() == ".pdf":
            pdf_path = f
            break
            
    with pdfplumber.open(str(pdf_path)) as pdf:
        page = pdf.pages[0]
        words = page.extract_words(keep_blank_chars=False)
        print(f"Mathematical center: {page.width / 2.0}")
        gutter_center = find_gutter(words, float(page.width))

if __name__ == "__main__":
    test()
