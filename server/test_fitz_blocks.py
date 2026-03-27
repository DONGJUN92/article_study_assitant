import fitz

def test():
    pdf_path = "data/documents/91cb5d98ff89115f/Week5_Priester_2004_JCR.pdf"
    
    # Just an arbitrary doc if the above doesn't exist
    from glob import glob
    files = glob("data/documents/*/*.pdf")
    if not files: return
    pdf_path = files[0]

    doc = fitz.open(pdf_path)
    page = doc[0] # Try page 0 or 1
    
    # Text sort=True
    text1 = page.get_text("text", sort=True)
    print("--- SORT=TRUE ---")
    print(text1[-500:])

if __name__ == "__main__":
    test()
