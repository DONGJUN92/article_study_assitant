from services.pdf_service import pdf_service
from config import DOCUMENTS_DIR
import json

def test():
    # Pick the first ingested document directory that has a PDF
    docs = [d for d in DOCUMENTS_DIR.iterdir() if d.is_dir()]
    if not docs:
        print("No docs found")
        return
        
    doc_id = docs[0].name
    pdf_path = None
    for f in docs[0].iterdir():
        if f.suffix.lower() == ".pdf":
            pdf_path = f
            break
            
    if not pdf_path:
        print("No PDF found in doc dir")
        return
        
    print(f"Testing smart extraction on {pdf_path.name} ...")
    
    # Read raw bytes and re-extract
    raw_bytes = pdf_path.read_bytes()
    # Temporarily set doc_id to avoid overwriting or just process and print
    # Let's just use the service but print the first few sentences
    result = pdf_service.extract_from_bytes(raw_bytes, pdf_path.name)
    
    # Print the first 10 sentences to see if they make sense 
    # and aren't overlapping halfway through.
    sentences = result.get('sentence_map', [])
    print(f"\n--- EXTRACTED {len(sentences)} SENTENCES ---")
    
    # Just print the first 1500 chars of full text to verify columns are processed nicely
    print("\n--- FULL TEXT PREVIEW ---")
    print(result.get('full_text', '')[:1500])
    print("-------------------------\n")
    print("Test Complete.")

if __name__ == "__main__":
    test()
