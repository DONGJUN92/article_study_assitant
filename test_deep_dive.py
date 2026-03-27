from services.pdf_service import pdf_service
from pathlib import Path

def test_ingest():
    # Use Chaiken 1980 if possible, or any other
    pdf_path = Path("data/documents/42974dfe2632d777/Week5_Chaiken_1980_JPSP.pdf")
    if not pdf_path.exists():
        pdfs = list(Path("data/documents").rglob("*.pdf"))
        if pdfs:
            pdf_path = pdfs[0]
        else:
            print("No pdfs left to test")
            return
            
    print(f"Using {pdf_path}")
    raw = pdf_path.read_bytes()
    
    try:
        res = pdf_service.extract_from_bytes(raw, "testing_deep_dive.pdf")
        sm = res["sentence_map"]
        print(f"Total sentences: {len(sm)}")
        for i, s in enumerate(sm[:10]):
            print(f"[{i}] {s['text']}")
            print(f"    Rects: {s['rects']}")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ingest()
