import fitz
from pathlib import Path

def get_reading_order_blocks(page):
    words = page.get_text("words")
    if not words: return []
    
    page_width = page.rect.width
    mid_x = page_width / 2
    margin = 20 # 20 points margin around the center
    
    # 1. Group words into horizontal lines
    lines = []
    # Sort words by y0, then x0
    words.sort(key=lambda w: (w[1], w[0]))
    
    current_line = []
    current_y = -1
    for w in words:
        y_center = (w[1] + w[3]) / 2
        # if vertical distance is small, same line
        if current_line and abs(y_center - current_y) < 5:
            current_line.append(w)
        else:
            if current_line:
                lines.append(current_line)
            current_line = [w]
            current_y = y_center
    if current_line:
        lines.append(current_line)
        
    # 2. Classify lines as full-width, left, or right
    classified_blocks = [] # (type, y0, line_words)
    
    for line in lines:
        line_x0 = min(w[0] for w in line)
        line_x1 = max(w[2] for w in line)
        
        # If line crosses the middle margin significantly
        if line_x0 < mid_x - margin and line_x1 > mid_x + margin:
            l_type = "full"
        elif line_x1 <= mid_x + margin:
            l_type = "left"
        else:
            l_type = "right"
            
        classified_blocks.append({
            "type": l_type,
            "y0": min(w[1] for w in line),
            "words": line
        })
        
    # 3. Assemble sequential reading order
    # Heuristic: Read full width blocks top-down, but if we hit columns, read left column till a break, then right.
    # To keep it simple: group continuous sections of the page by vertical 'zones'.
    # A zone is separated by a 'full' width block.
    
    zones = []
    current_zone = {"full": [], "left": [], "right": []}
    
    for b in classified_blocks:
        if b["type"] == "full":
            if current_zone["left"] or current_zone["right"]:
                zones.append(current_zone)
                current_zone = {"full": [], "left": [], "right": []}
            current_zone["full"].append(b)
        else:
            current_zone[b["type"]].append(b)
    if any(current_zone.values()):
        zones.append(current_zone)
        
    final_sentences = []
    
    def process_block_list(blist):
        if not blist: return
        # Sort lines strictly by y0
        blist.sort(key=lambda b: b["y0"])
        # extract text
        text_parts = []
        for b in blist:
            b["words"].sort(key=lambda w: w[0]) # sort by x
            text_parts.append(" ".join(w[4] for w in b["words"]))
        text = " ".join(text_parts)
        # We can split by sentences or just return as one block
        final_sentences.append(text)
        
    for z in zones:
        process_block_list(z["full"])
        process_block_list(z["left"])
        process_block_list(z["right"])
        
    return final_sentences

def test():
    pdf_path = Path("data/documents/42974dfe2632d777/Week5_Chaiken_1980_JPSP.pdf")
    if not pdf_path.exists():
        pdf_path = list(Path("data/documents").rglob("*.pdf"))[0]
        
    doc = fitz.open(str(pdf_path))
    texts = get_reading_order_blocks(doc[0])
    
    print("--- CUSTOM 2-COLUMN SORTER EXTRACT ---")
    for i, t in enumerate(texts[:10]):
        print(f"BLOCK {i}:\n{t[:150]}\n")

if __name__ == "__main__":
    test()
