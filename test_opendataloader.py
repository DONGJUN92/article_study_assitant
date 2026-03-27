import os
from pathlib import Path
import json

def test_parse():
    # 1. Create a dummy pdf or use one if exists
    test_pdf = Path("test.pdf")
    if not test_pdf.exists():
        print("Please provide a test.pdf")
        
        # Let's create a minimal PDF using fpdf (if installed, but we don't have it). 
        # But wait, we can just check if any pdf exists in data/documents
        pass

    import opendataloader_pdf
    out_dir = Path("test_out")
    out_dir.mkdir(exist_ok=True)
    
    docs_dir = Path("data/documents")
    pdf_files = list(docs_dir.rglob("*.pdf"))
    
    if pdf_files:
        test_pdf = pdf_files[0]
        print(f"Testing with {test_pdf}")
        
        opendataloader_pdf.convert(
            input_path=[str(test_pdf)],
            output_dir=str(out_dir),
            format="json"
        )
        
        json_file = out_dir / f"{test_pdf.stem}.json"
        if json_file.exists():
            data = json.loads(json_file.read_text(encoding="utf-8"))
            print("=== JSON KEYS ===")
            if isinstance(data, dict):
                print(data.keys())
                if "elements" in data:
                    print(f"Has {len(data['elements'])} elements")
                    if data["elements"]:
                        print("Sample Element:", data["elements"][0])
                elif "pages" in data:
                    print("Has pages")
            elif isinstance(data, list):
                print("It's a list. Length:", len(data))
                if data:
                    print("Sample element:", data[0])
            else:
                print("Unknown structure:", type(data))
        else:
            print(f"JSON not generated at {json_file}")
    else:
        print("No PDF files found to test.")

if __name__ == "__main__":
    test_parse()
