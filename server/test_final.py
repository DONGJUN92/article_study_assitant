from services.pdf_service import pdf_service
from config import DOCUMENTS_DIR

def test():
    docs = [d for d in DOCUMENTS_DIR.iterdir() if d.is_dir()]
    pdf_path = next(f for f in docs[0].iterdir() if f.suffix.lower() == ".pdf")
    
    print(f"Testing extraction on {pdf_path.name} ...")
    raw_bytes = pdf_path.read_bytes()
    
    result = pdf_service.extract_from_bytes(raw_bytes, pdf_path.name)
    sentences = result.get('sentence_map', [])
    
    print("\n--- SENTENCE MAP CHECK ---")
    for s in sentences:
        text = s['text']
        if "message content" in text or "based cognitions" in text or "CQ" in text or "fa" in text or "systematic view of persuasion" in text:
            print(f"> {text[:150]}\n")
                
    print("Test Complete.")

if __name__ == "__main__":
    test()
