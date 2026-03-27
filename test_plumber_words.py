import pdfplumber
from pathlib import Path

def test_plumber_words():
    pdf_path = Path("data/documents/42974dfe2632d777/Week5_Chaiken_1980_JPSP.pdf")
    if not pdf_path.exists():
        pdf_path = list(Path("data/documents").rglob("*.pdf"))[0]
        
    with pdfplumber.open(str(pdf_path)) as pdf:
        page = pdf.pages[0]
        
        words = page.extract_words(extra_attrs=["size"])
        print(f"Total words: {len(words)}")
        
        # Print the first 100 words to check order
        text = " ".join([w["text"] for w in words[:150]])
        print("--- EXTRACT_WORDS ---")
        print(text)

if __name__ == "__main__":
    test_plumber_words()
