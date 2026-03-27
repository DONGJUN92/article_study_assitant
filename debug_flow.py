import pdfplumber
from services.pdf_service import pdf_service
from config import DOCUMENTS_DIR

def test():
    docs = [d for d in DOCUMENTS_DIR.iterdir() if d.is_dir()]
    pdf_path = next(f for f in docs[0].iterdir() if f.suffix.lower() == ".pdf")
    
    with pdfplumber.open(str(pdf_path)) as pdf:
        page = pdf.pages[0]
        
        page_width = float(page.width)
        center_start = page_width * 0.35
        center_mid = page_width * 0.50
        center_end = page_width * 0.65
        
        words = page.extract_words(keep_blank_chars=False)
        left_x1s = [round(w['x1']) for w in words if center_start < w['x1'] < (center_mid + page_width * 0.05)]
        right_x0s = [round(w['x0']) for w in words if (center_mid - page_width * 0.05) < w['x0'] < center_end]
        
        if left_x1s and right_x0s:
            from collections import Counter
            best_left_x1 = Counter(left_x1s).most_common(1)[0][0]
            best_right_x0 = Counter(right_x0s).most_common(1)[0][0]
            if best_left_x1 < best_right_x0:
                center_x = (best_left_x1 + best_right_x0) / 2.0
            else:
                center_x = page_width / 2.0
        else:
            center_x = page_width / 2.0
            
        gutter_margin = page_width * 0.015

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

        blocks = []
        current_block = None

        print("--- LINE CLASSIFICATION ---")
        for line in lines:
            min_x = min(w['x0'] for w in line)
            max_x = max(w['x1'] for w in line)

            w_type = 'split'
            has_spanning = False
            if min_x < (center_x - gutter_margin) and max_x > (center_x + gutter_margin):
                for w in line:
                    if w['x0'] < (center_x - gutter_margin) and w['x1'] > (center_x + gutter_margin):
                        has_spanning = True
                        break
                w_type = 'spanning' if has_spanning else 'split'
            
            # Print if this line has the problematic text
            text = " ".join(w['text'] for w in line)
            if "CQ d" in text or "based cognitions" in text or "detailed processing" in text:
                print(f"LINE TYPE: {w_type}, TEXT: {text}")

if __name__ == "__main__":
    test()
