import pdfplumber
from config import DOCUMENTS_DIR

def test_fix():
    docs = [d for d in DOCUMENTS_DIR.iterdir() if d.is_dir()]
    pdf_path = next(f for f in docs[0].iterdir() if f.suffix.lower() == ".pdf")
    
    with pdfplumber.open(str(pdf_path)) as pdf:
        page = pdf.pages[0]
        words = page.extract_words(keep_blank_chars=False)
        page_width = float(page.width)
        
        center_start = page_width * 0.35
        center_mid = page_width * 0.50
        center_end = page_width * 0.65
        
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
        
        # FIX: Track the top coordinate of the line's start!
        current_line_top = words[0]['top']

        for w in words:
            if w['top'] <= current_line_top + 8:
                current_line.append(w)
            else:
                lines.append(current_line)
                current_line = [w]
                current_line_top = w['top']

        if current_line:
            lines.append(current_line)

        # 2. Determine type of line
        typed_lines = []
        for line in lines:
            min_x = min(w['x0'] for w in line)
            max_x = max(w['x1'] for w in line)

            w_type = 'split'
            if min_x < (center_x - gutter_margin) and max_x > (center_x + gutter_margin):
                has_spanning = False
                for w in line:
                    if w['x0'] < (center_x - gutter_margin) and w['x1'] > (center_x + gutter_margin):
                        has_spanning = True
                        break
                w_type = 'spanning' if has_spanning else 'split'

            typed_lines.append({'type': w_type, 'words': line})
            
        # 3. Blocks
        blocks = []
        current_block = {'type': typed_lines[0]['type'], 'lines': [typed_lines[0]['words']]}
        for t_line in typed_lines[1:]:
            if t_line['type'] == current_block['type']:
                current_block['lines'].append(t_line['words'])
            else:
                blocks.append(current_block)
                current_block = {'type': t_line['type'], 'lines': [t_line['words']]}
        blocks.append(current_block)
        
        # 4. Extract
        final_words = []
        for block in blocks:
            if block['type'] == 'spanning':
                b_words = [w for line in block['lines'] for w in line]
                b_words.sort(key=lambda w: (w['top'] // 8, w['x0']))
                final_words.extend(b_words)
            else:
                left_words = []
                right_words = []
                for line in block['lines']:
                    for w in line:
                        mid_x = (w['x0'] + w['x1']) / 2.0
                        if mid_x < center_x:
                            left_words.append(w)
                        else:
                            right_words.append(w)
                
                left_words.sort(key=lambda w: (w['top'] // 8, w['x0']))
                right_words.sort(key=lambda w: (w['top'] // 8, w['x0']))
                
                final_words.extend(left_words)
                final_words.extend(right_words)
                
        text = " ".join(w['text'] for w in final_words)
        idx = text.find("In essence, a systematic view")
        if idx != -1:
            print("RESULT:", text[idx:idx+350])
            
if __name__ == "__main__":
    test_fix()
