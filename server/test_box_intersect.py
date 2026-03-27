import fitz

def intersects(w_rect, b_rect):
    # w_rect: [wx0, wy0, wx1, wy1], b_rect: [bx0, by0, bx1, by1]
    # Check if rectangles overlap
    if w_rect[2] < b_rect[0] or w_rect[0] > b_rect[2]: return False
    if w_rect[3] < b_rect[1] or w_rect[1] > b_rect[3]: return False
    return True

def test():
    pdf_path = "data/documents/42974dfe2632d777/Week5_Chaiken_1980_JPSP.pdf" # This was the file from previous test 
    
    doc = fitz.open(pdf_path)
    page = doc[0]
    
    # Simulate a bounding box from OpenDataLoader that isolates the left column
    # The whole merged block was: 20.9, 359.1 (top left)
    # Let's say Docling found left column: x: 20 -> 280, y: 359 -> 500
    mock_box = [20.0, 350.0, 280.0, 500.0]
    
    all_words = page.get_text("words")
    
    inside_words = []
    for w in all_words:
        w_rect = [w[0], w[1], w[2], w[3]]
        text = w[4]
        if intersects(w_rect, mock_box):
            inside_words.append({
                "text": text,
                "rect": w_rect,
                "x0": w[0],
                "y0": w[1]
            })
            
    # Sort geometrically: line by line. Threshold for same line: 5 points
    inside_words.sort(key=lambda w: (round(w["y0"] / 5) * 5, w["x0"]))
    
    print("--- EXTRACTED WORDS FROM LEFT COLUMN ---")
    print(" ".join([w["text"] for w in inside_words]))

if __name__ == "__main__":
    test()
