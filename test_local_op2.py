import json
from pathlib import Path

def run():
    out_dir = Path("test_out2")
    test_pdf = Path("data/documents/5a71ce1a84b92665/Week3_Mohsenin_2025_JCR.pdf")
    json_file = out_dir / f"{test_pdf.stem}.json"
    if json_file.exists():
        data = json.loads(json_file.read_text(encoding="utf-8"))
        if "kids" in data:
            print("Kids (pages) length:", len(data["kids"]))
            page0 = data["kids"][0]
            print("Page 0 keys:", page0.keys())
            if "kids" in page0:
                print("Page 0 has kids (elements):", len(page0["kids"]))
                print("First element in page 0:", page0["kids"][0])
                print("Second element:", page0["kids"][1] if len(page0["kids"]) > 1 else None)
        else:
            print("No kids array found")

if __name__ == "__main__":
    run()
