import fitz
from config import DOCUMENTS_DIR

def _extract_words_smart_layout_fitz(page_width, fitz_words, line_tolerance=8):
    words = []
    for w in fitz_words:
        words.append({
            'x0': w[0],
            'top': w[1],
            'x1': w[2],
            'bottom': w[3],
            'text': w[4],
            'block_n': w[5]
        })
        
    if not words: return []
    
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

    # Group lines PER BLOCK to prevent tall watermarks in block X from swallowing text in block Y
    final_words = []
    
    # Sort blocks natively
    blocks_dict = {}
    for w in words:
        blocks_dict.setdefault(w['block_n'], []).append(w)
        
    for b_num in sorted(blocks_dict.keys()):
        b_words = blocks_dict[b_num]
        
        b_words.sort(key=lambda w: (w['top'], w['x0']))
        lines = []
        current_line = []
        current_line_top = b_words[0]['top']

        for w in b_words:
            if w['top'] <= current_line_top + line_tolerance:
                current_line.append(w)
            else:
                lines.append(current_line)
                current_line = [w]
                current_line_top = w['top']
        if current_line:
            lines.append(current_line)

        # spanning or split
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
            
        sub_blocks = []
        current_sub = {'type': typed_lines[0]['type'], 'lines': [typed_lines[0]['words']]}
        for t_line in typed_lines[1:]:
            if t_line['type'] == current_sub['type']:
                current_sub['lines'].append(t_line['words'])
            else:
                sub_blocks.append(current_sub)
                current_sub = {'type': t_line['type'], 'lines': [t_line['words']]}
        sub_blocks.append(current_sub)
        
        # Output words
        for sb in sub_blocks:
            if sb['type'] == 'spanning':
                sb_words = [w for line in sb['lines'] for w in line]
                sb_words.sort(key=lambda w: (w['top'] // line_tolerance, w['x0']))
                final_words.extend(sb_words)
            else:
                left_words = []
                right_words = []
                for line in sb['lines']:
                    for w in line:
                        mid_x = (w['x0'] + w['x1']) / 2.0
                        if mid_x < center_x:
                            left_words.append(w)
                        else:
                            right_words.append(w)
                
                left_words.sort(key=lambda w: (w['top'] // line_tolerance, w['x0']))
                right_words.sort(key=lambda w: (w['top'] // line_tolerance, w['x0']))
                
                final_words.extend(left_words)
                final_words.extend(right_words)
                
    return final_words

def test():
    docs = [d for d in DOCUMENTS_DIR.iterdir() if d.is_dir()]
    pdf_path = next(f for f in docs[0].iterdir() if f.suffix.lower() == ".pdf")
    
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    fitz_words = page.get_text("words")
    rect = page.rect
    page_width = True and rect.width
    
    sorted_words = _extract_words_smart_layout_fitz(page_width, fitz_words)
    text = " ".join(w['text'] for w in sorted_words)
    
    idx = text.find("In essence, a systematic view")
    if idx != -1:
        print("RESULT:")
        print(text[idx:idx+350])
        print("\nCQ inside the extracted window?", "CQ d fa" in text[idx:idx+350])
        
if __name__ == "__main__":
    test()
