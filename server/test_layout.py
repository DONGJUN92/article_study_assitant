from services.pdf_service import pdf_service
from config import DOCUMENTS_DIR

def test():
    # Get arbitrary doc
    docs = [d.name for d in DOCUMENTS_DIR.iterdir() if d.is_dir()]
    if not docs:
        print("No docs found")
        return
    
    doc_id = docs[0]
    print(f"Testing layout render for doc: {doc_id}")
    
    img_bytes = pdf_service.render_page_layout(doc_id, 1)
    if img_bytes:
        with open("test_layout_out.png", "wb") as f:
            f.write(img_bytes)
        print("Saved test_layout_out.png successfully.")
    else:
        print("Failed to render layout")

if __name__ == "__main__":
    test()
