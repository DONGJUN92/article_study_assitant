import pdfplumber
from services.pdf_service import pdf_service
from config import DOCUMENTS_DIR

def test():
    docs = [d for d in DOCUMENTS_DIR.iterdir() if d.is_dir()]
    pdf_path = None
    for f in docs[0].iterdir():
        if f.suffix.lower() == ".pdf":
            pdf_path = f
            break
            
    with pdfplumber.open(str(pdf_path)) as pdf:
        page = pdf.pages[0]
        page_width = float(page.width)
        center_x = page_width / 2.0
        gutter_margin = page_width * 0.02
        
        words = page.extract_words(keep_blank_chars=False)
        words.sort(key=lambda w: (w['top'], w['x0']))
        lines = []
        current_line = []
        current_bottom = words[0]['bottom']
        
        for w in words:
            if w['top'] <= current_bottom + 8:
                current_line.append(w)
                current_bottom = max(current_bottom, w['bottom'])
            else:
                lines.append(current_line)
                current_line = [w]
                current_bottom = w['bottom']
        if current_line:
            lines.append(current_line)
            
        print(f"Center: {center_x}, Margin: {gutter_margin}, Core: {center_x - gutter_margin} to {center_x + gutter_margin}")
        
        for i, line in enumerate(lines):
            text = " ".join(w['text'] for w in line)
            if "In contrast" in text or "dissertation" in text:
                print(f"--- Line {i} ---")
                print("Text:", text)
                min_x = min(w['x0'] for w in line)
                max_x = max(w['x1'] for w in line)
                print(f"min_x: {min_x}, max_x: {max_x}")
                
                has_spanning = False
                for w in line:
                    if w['x0'] < (center_x + gutter_margin) and w['x1'] > (center_x - gutter_margin):
                        print(f"SPANNING WORD: '{w['text']}' -> x0:{w['x0']}, x1:{w['x1']}")
                        has_spanning = True
                
                print(f"Type: {'spanning' if has_spanning else 'split'}\n")

if __name__ == "__main__":
    test()
