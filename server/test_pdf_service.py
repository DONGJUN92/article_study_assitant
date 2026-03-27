import asyncio
from services.pdf_service import pdf_service
from pathlib import Path
from glob import glob

async def test_ingest():
    files = glob("data/documents/*/*.pdf")
    if not files:
        print("No PDF found.")
        return
    pdf_path = Path(files[-1])
    print(f"Testing with {pdf_path}")

    print("Extracting bytes via modified PDFService...")
    raw = pdf_path.read_bytes()
    
    res = pdf_service.extract_from_bytes(raw, filename="test_output.pdf")
    
    print("\n--- TEST SUCCESS ---")
    print(f"Chunks generated: {len(res['chunks'])}")
    print(f"Sentence map length: {len(res['sentence_map'])}")
    print(f"Pages: {len(res['pages'])}")
    if res['sentence_map']:
        print("Sample sentence rects:")
        for s in res['sentence_map'][:3]:
            print(f"- {s['text'][:50]} -> Rects: {s['rects']}")

if __name__ == "__main__":
    asyncio.run(test_ingest())
