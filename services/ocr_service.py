import numpy as np

class OCRService:
    def __init__(self):
        self._ocr = None

    @property
    def ocr(self):
        if self._ocr is None:
            import os
            os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
            os.environ['FLAGS_enable_pir_api'] = '0' # Fix for PaddlePaddle 3.3.1 crash on Windows CPU
            from paddleocr import PaddleOCR
            
            # use_angle_cls=True to handle rotated text, lang='en' since these are mostly english papers.
            # Removed show_log as it is not supported in recent versions
            self._ocr = PaddleOCR(use_angle_cls=True, lang='en')
        return self._ocr

    def extract_words(self, image_bytes: bytes) -> list:
        """
        Extract words from an image using PaddleOCR.
        Returns a list of dicts compatible with the PyMuPDF layout algorithm,
        including synthesized line_n and word_n attributes.
        """
        import cv2
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        result = self.ocr.ocr(img)
        words = []
        if not result or not result[0]:
            return words
            
        page_res = result[0]
        
        if isinstance(page_res, dict):
            # PaddleOCR 3.x format
            polys = page_res.get('dt_polys', [])
            texts = page_res.get('rec_texts', [])
            
            for i in range(min(len(polys), len(texts))):
                box = polys[i]
                text = texts[i]
                if not text.strip():
                    continue
                xs = [pt[0] for pt in box]
                ys = [pt[1] for pt in box]
                words.append({
                    'x0': float(min(xs)),
                    'top': float(min(ys)),
                    'x1': float(max(xs)),
                    'bottom': float(max(ys)),
                    'text': text,
                    'block_n': 0,
                })
        else:
            # PaddleOCR 2.x format
            for line in page_res:
                if not line:
                    continue
                
                try:
                    if len(line) == 2:
                        box, (text, score) = line
                    elif len(line) == 3:
                        box, text, score = line
                    else:
                        box, text = line[0], line[1]
                except Exception:
                    box, text = line[0], line[1][0]
                    
                xs = [pt[0] for pt in box]
                ys = [pt[1] for pt in box]
                words.append({
                    'x0': float(min(xs)),
                    'top': float(min(ys)),
                    'x1': float(max(xs)),
                    'bottom': float(max(ys)),
                    'text': text,
                    'block_n': 0,
                })
            
        if not words:
            return []

        # Synthesize line_n and word_n via geometric clustering
        words.sort(key=lambda w: (w['top'], w['x0']))
        
        line_n = 0
        current_bottom = words[0]['bottom']
        current_top = words[0]['top']
        
        for w in words:
            height = w['bottom'] - w['top']
            # If word top overlaps with the current baseline by at least a small margin
            if w['top'] <= current_bottom - (height * 0.2): 
                w['line_n'] = line_n
                current_bottom = max(current_bottom, w['bottom'])
            else:
                line_n += 1
                w['line_n'] = line_n
                current_bottom = w['bottom']
                
        # Assign word_n based on X coordinate within each synthesized line
        words.sort(key=lambda w: (w['line_n'], w['x0']))
        current_l = -1
        w_idx = 0
        for w in words:
            if w['line_n'] != current_l:
                current_l = w['line_n']
                w_idx = 0
            w['word_n'] = w_idx
            w_idx += 1
            
        return words

ocr_service = OCRService()
