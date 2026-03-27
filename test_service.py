from services.pdf_service import pdf_service
from config import DOCUMENTS_DIR
import sys

# Windows console fix for cp949
sys.stdout.reconfigure(encoding='utf-8')

def test():
    docs = [d for d in DOCUMENTS_DIR.iterdir() if d.is_dir()]
    if not docs:
        print("No docs found.")
        return
    
    pdf_path = next(f for f in docs[0].iterdir() if f.suffix.lower() == ".pdf")
    print(f"Testing extraction on {pdf_path.name} ...")
    raw_bytes = pdf_path.read_bytes()
    
    result = pdf_service.extract_from_bytes(raw_bytes, pdf_path.name)
    sentences = result.get('sentence_map', [])
    
    print("\n--- SENTENCE MAP CHECK ---")
    for s in sentences:
        text = s['text']
        # Let's target the exact text from the user's latest screenshot which had mixing lines
        if "In the systematic view, recipients" in text or "Conversely, in the heuristic view" in text or "avoid detailed process" in text:
            print(f"> {text[:300]}\n")
            
    print("Test Complete.")

if __name__ == "__main__":
    test()
