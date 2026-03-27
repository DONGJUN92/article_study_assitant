import fitz

def test():
    from glob import glob
    files = glob("data/documents/*/*.pdf")
    if not files:
        print("No PDF found")
        return
    pdf_path = files[0]
    print(f"Testing {pdf_path}")

    doc = fitz.open(pdf_path)
    page = doc[0] # Try page 0
    
    blocks = page.get_text("blocks")
    # blocks is a list of (x0, y0, x1, y1, "lines in block", block_no, block_type)
    print(f"Found {len(blocks)} blocks on page 0")
    for b in blocks[-5:]:
        # Print coordinates and text
        x0, y0, x1, y1, text, b_no, b_ty = b
        print(f"Block {b_no} at ({x0:.1f}, {y0:.1f}):\n{text.strip()[:100]}\n")

if __name__ == "__main__":
    test()
