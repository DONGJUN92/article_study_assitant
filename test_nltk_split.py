from services.pdf_service import pdf_service
from config import DOCUMENTS_DIR

def test():
    # Find a document
    docs = [d for d in DOCUMENTS_DIR.iterdir() if d.is_dir()]
    pdf_path = next(f for f in docs[0].iterdir() if f.suffix.lower() == ".pdf")
    
    print(f"Testing NLTK extraction on {pdf_path.name} ...")
    raw_bytes = pdf_path.read_bytes()
    
    # Run pipeline
    result = pdf_service.extract_from_bytes(raw_bytes, pdf_path.name)
    sentences = result.get('sentence_map', [])
    
    # Find sentences that contain abbreviations
    print("\n--- SENTENCES CONTAINING ABBREVIATIONS ---")
    count = 0
    for s in sentences:
        text = s['text']
        if "e.g." in text or "et al." in text or "i.e." in text:
            print(f"> {text}\n")
            count += 1
            if count >= 10:
                break
                
    print("Test Complete.")

if __name__ == "__main__":
    test()
