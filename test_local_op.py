import json
from pathlib import Path

def run():
    try:
        import opendataloader_pdf
    except ImportError:
        print("Not installed yet.")
        return

    test_pdf = Path("data/documents/5a71ce1a84b92665/Week3_Mohsenin_2025_JCR.pdf")
    if not test_pdf.exists():
        print(f"File {test_pdf} not found.")
        return

    out_dir = Path("test_out2")
    out_dir.mkdir(exist_ok=True)

    print("Running opendataloader_pdf...")
    try:
        opendataloader_pdf.convert(
            input_path=[str(test_pdf)],
            output_dir=str(out_dir),
            format="json"
            # no hybrid
        )
    except Exception as e:
        print("Convert failed:", e)

    json_file = out_dir / f"{test_pdf.stem}.json"
    if json_file.exists():
        data = json.loads(json_file.read_text(encoding="utf-8"))
        if "elements" in data:
            for el in data["elements"][:3]:
                print(el)
        else:
            print("KEYS:", data.keys())

if __name__ == "__main__":
    run()
