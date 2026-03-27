import pdfplumber
from services.pdf_service import pdf_service
from config import DOCUMENTS_DIR

def get_dynamic_center(words, page_width):
    search_start = page_width * 0.3
    search_end = page_width * 0.7
    
    center_words = [w for w in words if w['x1'] > search_start and w['x0'] < search_end]
    intervals = [(w['x0'], w['x1'], w['text']) for w in center_words]
    intervals.sort(key=lambda x: x[0])
    
    merged = []
    for interval in intervals:
        if not merged:
            merged.append([interval[0], interval[1], [interval[2]]])
        else:
            last = merged[-1]
            if interval[0] <= last[1]:
                last[1] = max(last[1], interval[1])
                last[2].append(interval[2])
            else:
                merged.append([interval[0], interval[1], [interval[2]]])
                
    for m in merged:
        print(f"Interval {m[0]:.1f} to {m[1]:.1f}: {len(m[2])} words. Example: {m[2][:5]}")
        
    for i in range(len(merged)-1):
        print(f"Gap {i}: {merged[i+1][0] - merged[i][1]:.1f}")

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
        get_dynamic_center(words, float(page.width))

if __name__ == "__main__":
    test()
