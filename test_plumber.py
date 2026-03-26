import pdfplumber
from pathlib import Path

def test_plumber():
    pdf_path = Path("data/documents/42974dfe2632d777/Week5_Chaiken_1980_JPSP.pdf")
    if not pdf_path.exists():
        pdf_path = list(Path("data/documents").rglob("*.pdf"))[0]
        
    print(f"Testing pdfplumber on {pdf_path}")
    
    with pdfplumber.open(str(pdf_path)) as pdf:
        page = pdf.pages[0]
        
        # Test standard text extraction with layout hints
        text = page.extract_text(layout=True)
        print("--- EXTRACT_TEXT(layout=True) ---")
        print(text[:1500])
        print("\n\n")
        
        # Test without layout
        text2 = page.extract_text()
        print("--- EXTRACT_TEXT() ---")
        print(text2[:1500])

if __name__ == "__main__":
    test_plumber()
