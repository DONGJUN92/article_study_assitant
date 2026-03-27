import pdfplumber
import re
from pathlib import Path

def generate_sentence_map():
    pdf_path = Path("data/documents/42974dfe2632d777/Week5_Chaiken_1980_JPSP.pdf")
    if not pdf_path.exists():
        pdf_path = list(Path("data/documents").rglob("*.pdf"))[0]
        
    sentence_map = []
    sent_regex = re.compile(r'[^.!?]+[.!?]+(?:\s|$)')
    
    with pdfplumber.open(str(pdf_path)) as pdf:
        page = pdf.pages[0]
        words = page.extract_words(keep_blank_chars=False)
        
        current_text = []
        current_rects = []
        
        for w in words:
            # pdfplumber rect: x0, top, x1, bottom
            # We want fitz style: x0, y0, x1, y1
            rect = [w["x0"], w["top"], w["x1"], w["bottom"]]
            text = w["text"]
            
            current_text.append(text)
            current_rects.append(rect)
            
            # Basic sentence boundary (ends with punctuation)
            # Or we can just join and regex split? 
            # It's safer to just join and regex split, then map rects!
            
        # Join words into full text
        full_text = " ".join([w["text"] for w in words])
        sentences = [m.group().strip() for m in sent_regex.finditer(full_text) if m.group().strip()]
        
        # Sequentially map rects based on characters consumed
        word_idx = 0
        num_words = len(words)
        
        for sent in sentences:
            sent_stripped = re.sub(r'\W', '', sent)
            target_len = len(sent_stripped)
            consumed_len = 0
            rects = []
            
            while word_idx < num_words and consumed_len < target_len:
                w = words[word_idx]
                rects.append([w["x0"], w["top"], w["x1"], w["bottom"]])
                consumed_len += len(re.sub(r'\W', '', w["text"]))
                word_idx += 1
                
            sentence_map.append({
                "text": sent,
                "rects": rects
            })

    print(f"Generated {len(sentence_map)} sentences on page 1.")
    for s in sentence_map[:5]:
        print(f"[{len(s['rects'])} RECTS] {s['text']}")

if __name__ == "__main__":
    generate_sentence_map()
