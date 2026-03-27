import re

def intersect(rect1, rect2):
    return not (rect1[2] < rect2[0] or rect1[0] > rect2[2] or rect1[3] < rect2[1] or rect1[1] > rect2[3])

def construct_sentence_rects(content, paragraph_box, all_words):
    # Filter words in box
    box_words = []
    if paragraph_box:
        for w in all_words:
            w_rect = [w[0], w[1], w[2], w[3]]
            # Add a small padding to intersection to be safe? 
            # If paragraph_box is exact, maybe standard intersection is fine
            # Let's use center point of word to be safe against slight overshoots
            cx = (w[0] + w[2])/2
            cy = (w[1] + w[3])/2
            if paragraph_box[0] <= cx <= paragraph_box[2] and paragraph_box[1] <= cy <= paragraph_box[3]:
                box_words.append({
                    "text": w[4],
                    "rect": w_rect,
                    "x0": w[0], "y0": w[1]
                })
    else:
        # If no box, just use all words (fallback)
        box_words = [{"text": w[4], "rect": [w[0], w[1], w[2], w[3]], "x0": w[0], "y0": w[1]} for w in all_words]

    # Sort geometrically: line by line (tolerance 5 coords)
    box_words.sort(key=lambda w: (round(w["y0"] / 5) * 5, w["x0"]))

    # Now we have sentences and we want to allocate box_words to them
    sent_regex = r'[^.!?]+[.!?]+(?:\s|$)'
    sentences = [m.group().strip() for m in re.finditer(sent_regex, content) if m.group().strip()]
    if not sentences and content:
        sentences = [content.strip()]
        
    sentence_map = []
    word_idx = 0
    num_words = len(box_words)

    for sent in sentences:
        sent_words = sent.split()
        rects = []
        
        # Consume words from box_words that match the sentence
        # We'll just consume the same number of words as sent_words, or slightly match them.
        # A simple greedy approach: count non-punctuation characters.
        target_len = len(re.sub(r'\W', '', sent))
        consumed_len = 0
        
        while word_idx < num_words and consumed_len < target_len:
            w = box_words[word_idx]
            rects.append(w["rect"])
            consumed_len += len(re.sub(r'\W', '', w["text"]))
            word_idx += 1
            
        sentence_map.append({
            "text": sent,
            "rects": rects
        })
        
    return sentence_map


def test():
    # Mock data
    content = "This is the first sentence. And here is the second one!"
    paragraph_box = [0, 0, 100, 100]
    all_words = [
        (10, 10, 20, 20, "This", 0, 0, 0),
        (25, 10, 35, 20, "is", 0, 0, 1),
        (40, 10, 50, 20, "the", 0, 0, 2),
        (55, 10, 70, 20, "first", 0, 0, 3),
        (75, 10, 95, 20, "sentence.", 0, 0, 4),
        (10, 30, 25, 40, "And", 0, 1, 0),
        (30, 30, 45, 40, "here", 0, 1, 1),
        (50, 30, 60, 40, "is", 0, 1, 2),
        (65, 30, 75, 40, "the", 0, 1, 3),
        (80, 30, 95, 40, "second", 0, 1, 4),
        (10, 50, 25, 60, "one!", 0, 2, 0)
    ]
    
    smap = construct_sentence_rects(content, paragraph_box, all_words)
    for s in smap:
        print(f"Sent: {s['text']}")
        print(f"Rects: {len(s['rects'])}")
        print(s['rects'])

if __name__ == "__main__":
    test()
