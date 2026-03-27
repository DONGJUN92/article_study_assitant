import pdfplumber
from services.pdf_service import pdf_service
from config import DOCUMENTS_DIR

def get_dynamic_center(words, page_width):
    # Find the largest empty X-interval in the middle 30-70% of the page
    search_start = page_width * 0.3
    search_end = page_width * 0.7
    
    # Create an array of text coverages
    # Just sort all words by x0
    center_words = [w for w in words if w['x1'] > search_start and w['x0'] < search_end]
    if not center_words:
        return page_width / 2.0
        
    # Project onto X axis
    intervals = []
    for w in center_words:
        intervals.append((w['x0'], w['x1']))
        
    # Merge overlapping intervals
    intervals.sort(key=lambda x: x[0])
    merged = []
    for interval in intervals:
        if not merged:
            merged.append(interval)
        else:
            last = merged[-1]
            if interval[0] <= last[1]: # overlap
                merged[-1] = (last[0], max(last[1], interval[1]))
            else:
                merged.append(interval)
                
    # Find the largest gap between merged intervals
    max_gap = 0
    best_center = page_width / 2.0
    for i in range(len(merged)-1):
        gap = merged[i+1][0] - merged[i][1]
        if gap > max_gap:
            max_gap = gap
            best_center = (merged[i][1] + merged[i+1][0]) / 2.0
            
    # If no gap found inside the center words, maybe it's 1-column?
    if max_gap < 5: # less than 5 points gap
        return page_width / 2.0
        
    return best_center

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
        center_x = get_dynamic_center(words, float(page.width))
        print(f"Mathematical center: {page.width / 2.0}")
        print(f"Dynamic center: {center_x}")

if __name__ == "__main__":
    test()
