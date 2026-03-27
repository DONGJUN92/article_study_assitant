import fitz
import pymupdf4llm
from pathlib import Path

def test_mupdf():
    pdf_path = Path("data/documents/42974dfe2632d777/Week5_Chaiken_1980_JPSP.pdf")
    if not pdf_path.exists():
        pdf_path = list(Path("data/documents").rglob("*.pdf"))[0]
        
    print(f"Testing pymupdf4llm on {pdf_path}")
    md_text = pymupdf4llm.to_markdown(str(pdf_path), pages=[0])
    
    print("--- MD TEXT (LAST 1000 CHARS) ---")
    print(md_text[-1000:])

if __name__ == "__main__":
    test_mupdf()
