"""PDF parsing service using PyMuPDF."""
from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import pdfplumber
import fitz
from langdetect import detect
from services.ocr_service import ocr_service

import nltk
from nltk.tokenize import sent_tokenize

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', quiet=True)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

from config import DOCUMENTS_DIR, CHUNK_SIZE, CHUNK_OVERLAP


class PDFService:
    """Extract and chunk text from PDF documents."""

    @staticmethod
    def generate_doc_id(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()[:16]

    @staticmethod
    def clean_pdf_text(text: str) -> str:
        blocks = text.split("\n\n")
        cleaned_blocks = []
        for block in blocks:
            import re
            # remove hyphens at line ends
            b = re.sub(r'-\n\s*', '', block)
            # replace remaining single newlines with space
            b = b.replace('\n', ' ')
            # remove multi-spaces
            b = re.sub(r'[ \t]+', ' ', b)
            cleaned_blocks.append(b.strip())
        return "\n\n".join(b for b in cleaned_blocks if b)

    def _extract_words_smart_layout(self, page_width: float, words: List[dict]) -> List[dict]:
        """
        Extract words applying a smart gutter layout heuristic and PyMuPDF block/line numbers.
        This entirely eliminates geometric clustering (top // 8), preventing vertical line overlap.
        """
        if not words:
            return []
            
        center_start = page_width * 0.35
        center_mid = page_width * 0.50
        center_end = page_width * 0.65
        
        left_x1s = [round(w['x1']) for w in words if center_start < w['x1'] < (center_mid + page_width * 0.05)]
        right_x0s = [round(w['x0']) for w in words if (center_mid - page_width * 0.05) < w['x0'] < center_end]
        
        if left_x1s and right_x0s:
            from collections import Counter
            best_left_x1 = Counter(left_x1s).most_common(1)[0][0]
            best_right_x0 = Counter(right_x0s).most_common(1)[0][0]
            if best_left_x1 < best_right_x0:
                center_x = (best_left_x1 + best_right_x0) / 2.0
            else:
                center_x = page_width / 2.0
        else:
            center_x = page_width / 2.0
            
        gutter_margin = page_width * 0.015  # 1.5% margin

        # Group words by PyMuPDF block numbers to prevent hidden layers/watermarks from interleaving
        blocks_dict = {}
        for w in words:
            blocks_dict.setdefault(w.get('block_n', 0), []).append(w)
            
        final_words = []
        
        for b_num in sorted(blocks_dict.keys()):
            b_words = blocks_dict[b_num]
            
            # Group into lines purely by fitz native line_n
            line_dict = {}
            for w in b_words:
                line_dict.setdefault(w.get('line_n', 0), []).append(w)
                
            lines = []
            for l_num in sorted(line_dict.keys()):
                # Sort words within the visual line natively by PyMuPDF's word sequence number
                line_words = line_dict[l_num]
                line_words.sort(key=lambda w: w.get('word_n', 0))
                lines.append(line_words)

            typed_lines = []
            for line in lines:
                min_x = min(w['x0'] for w in line)
                max_x = max(w['x1'] for w in line)

                w_type = 'split'
                if min_x < (center_x - gutter_margin) and max_x > (center_x + gutter_margin):
                    has_spanning = False
                    for w in line:
                        if w['x0'] < (center_x - gutter_margin) and w['x1'] > (center_x + gutter_margin):
                            has_spanning = True
                            break
                    w_type = 'spanning' if has_spanning else 'split'

                typed_lines.append({'type': w_type, 'words': line})

            sub_blocks = []
            if not typed_lines:
                continue
            current_sub = {'type': typed_lines[0]['type'], 'lines': [typed_lines[0]['words']]}
            for t_line in typed_lines[1:]:
                if t_line['type'] == current_sub['type']:
                    current_sub['lines'].append(t_line['words'])
                else:
                    sub_blocks.append(current_sub)
                    current_sub = {'type': t_line['type'], 'lines': [t_line['words']]}
            sub_blocks.append(current_sub)

            for sb in sub_blocks:
                if sb['type'] == 'spanning':
                    sb_words = [w for line in sb['lines'] for w in line]
                    # Sort primarily by sequential line number, then by word sequence
                    sb_words.sort(key=lambda w: (w.get('line_n', 0), w.get('word_n', 0)))
                    final_words.extend(sb_words)
                else:
                    left_words = []
                    right_words = []
                    for line in sb['lines']:
                        for w in line:
                            mid_x = (w['x0'] + w['x1']) / 2.0
                            if mid_x < center_x:
                                left_words.append(w)
                            else:
                                right_words.append(w)
                    left_words.sort(key=lambda w: (w.get('line_n', 0), w.get('word_n', 0)))
                    right_words.sort(key=lambda w: (w.get('line_n', 0), w.get('word_n', 0)))
                    final_words.extend(left_words)
                    final_words.extend(right_words)
                    
        return final_words

    def _needs_ocr(self, page_text: str, fitz_words: list) -> bool:
        """Heuristic to determine if a page is scanned or heavily corrupted and needs OCR."""
        if len(fitz_words) < 20: 
            return True # Likely a scanned image-only PDF
            
        import re
        page_text_clean = page_text.replace(" ", "").replace("\n", "")
        if not page_text_clean:
            return True
            
        alpha_chars = len(re.sub(r'[^a-zA-Z]', '', page_text_clean))
        total_chars = len(page_text_clean)
        
        # If less than 40% of the text is alphabetical, it's highly likely corrupted font mappings or heavy math.
        # But to be safe against math-heavy papers, we specifically check for known corruption tokens like "CQ d fa"
        if total_chars > 50 and (alpha_chars / total_chars) < 0.4:
            return True
            
        if "CQ d fa" in page_text or "} {" in page_text:
            return True
            
        return False

    def extract_from_url(self, url: str) -> dict:
        """Download & extract text from a PDF URL (file:// or http(s)://)."""
        import httpx
        resp = httpx.get(url, follow_redirects=True, timeout=60)
        resp.raise_for_status()
        return self.extract_from_bytes(resp.content, filename=url.split("/")[-1])

    def extract_from_base64(self, b64_data: str, filename: str = "document.pdf") -> dict:
        raw = base64.b64decode(b64_data)
        return self.extract_from_bytes(raw, filename)

    def extract_from_bytes(self, raw: bytes, filename: str = "document.pdf") -> dict:
        doc_id = self.generate_doc_id(raw)
        doc_dir = DOCUMENTS_DIR / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)

        pdf_path = doc_dir / filename
        pdf_path.write_bytes(raw)

        pages: List[dict] = []
        full_text_parts: List[str] = []
        sentence_map = []
        
        title = filename.replace(".pdf", "")

        try:
            doc = fitz.open(stream=raw, filetype="pdf")
            page_count = len(doc)
            pdf_metadata = doc.metadata or {}
            
            if pdf_metadata.get("title"):
                raw_title = str(pdf_metadata.get("title", "")).strip(" ()'")
                if len(raw_title) > 5:
                    title = raw_title
                    
            for i in range(page_count):
                page_num = i + 1
                page = doc[i]
                
                # fitz word: (x0, top, x1, bottom, text, block_n, line_n, word_n)
                fitz_words = page.get_text("words")
                
                # Check for OCR necessity based on preliminary extraction
                prelim_text = " ".join([w[4] for w in fitz_words]) if fitz_words else ""
                
                words = []
                if self._needs_ocr(prelim_text, fitz_words):
                    # Trigger OCR fallback for this page
                    # Render page to image at 150 DPI for fast OCR
                    pix = page.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("png")
                    
                    # ocr_service returns dicts: {x0, top, x1, bottom, text, block_n, line_n, word_n}
                    try:
                        words = ocr_service.extract_words(img_bytes)
                    except Exception as e:
                        print(f"OCR failed for page {page_num}: {e}")
                        words = []
                else:
                    for w in fitz_words:
                        words.append({
                            'x0': w[0],
                            'top': w[1],
                            'x1': w[2],
                            'bottom': w[3],
                            'text': w[4],
                            'block_n': w[5],
                            'line_n': w[6],
                            'word_n': w[7]
                        })
                
                if not words:
                    continue
                
                page_width = float(page.rect.width)
                sorted_words = self._extract_words_smart_layout(page_width, words)
                
                page_text = " ".join([w["text"] for w in sorted_words])
                pages.append({
                    "page": page_num,
                    "text": page_text
                })
                full_text_parts.append(page_text)
                
                page_text_clean = re.sub(r'\s+', ' ', page_text).strip()
                
                try:
                    tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
                except LookupError:
                    tokenizer = nltk.data.load('tokenizers/punkt_tab/english.pickle')
                
                tokenizer._params.abbrev_types.update(['al', 'e.g', 'i.e', 'fig', 'eq', 'vol', 'no', 'vs', 'cf'])
                
                sentences = tokenizer.tokenize(page_text_clean)
                
                merged_sents = []
                for s in sentences:
                    if merged_sents and re.match(r'^[a-z\(\[\,\;\:]', s.strip()):
                        merged_sents[-1] = merged_sents[-1] + " " + s
                    else:
                        merged_sents.append(s)
                sentences = merged_sents
                
                if not sentences and page_text_clean:
                    sentences = [page_text_clean]
                    
                word_idx = 0
                num_words = len(sorted_words)
                
                for sent in sentences:
                    sent_stripped = re.sub(r'\W', '', sent)
                    target_len = len(sent_stripped)
                    consumed_len = 0
                    rects = []
                    
                    while word_idx < num_words and consumed_len < target_len:
                        w = sorted_words[word_idx]
                        rects.append([w["x0"], w["top"], w["x1"], w["bottom"]])
                        w_text = str(w.get("text", ""))
                        consumed_len += len(re.sub(r'\W', '', w_text))
                        word_idx += 1
                        
                    sentence_map.append({
                        "page": page_num,
                        "text": sent,
                        "rects": rects
                    })
                    
            doc.close()

        except Exception as e:
            print(f"Extraction error: {e}")
            pass

        full_text = "\n\n".join(full_text_parts)

        # Detect language
        lang = "en"
        try:
            if full_text:
                sample = full_text[:3000]
                lang = detect(sample)
        except Exception:
            pass

        # Use textual title fallback if metadata failed
        if len(title) < 5 or "document.pdf" in title:
            for line in full_text.split("\n"):
                stripped = line.strip()
                if stripped and len(stripped) > 5:
                    title = stripped[:120]
                    break

        # Chunk text
        chunks = self._chunk_text(pages)

        metadata = {
            "doc_id": doc_id,
            "filename": filename,
            "title": title,
            "page_count": page_count,
            "language": lang,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "chunk_count": len(chunks),
        }

        # Save metadata
        (doc_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # Save full text for translation
        (doc_dir / "full_text.txt").write_text(full_text, encoding="utf-8")
        # Save pages
        (doc_dir / "pages.json").write_text(
            json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Save sentence map
        (doc_dir / "sentences.json").write_text(
            json.dumps(sentence_map, ensure_ascii=False, indent=2), encoding="utf-8"
        )


        return {**metadata, "chunks": chunks, "full_text": full_text, "pages": pages, "sentence_map": sentence_map}

    def _chunk_text(self, pages: List[dict]) -> List[dict]:
        """Split pages into overlapping chunks."""
        chunks: List[dict] = []
        chunk_id = 0

        for page_info in pages:
            page_num = page_info["page"]
            text = page_info["text"]
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

            current_chunk = ""
            for para in paragraphs:
                if len(current_chunk.split()) + len(para.split()) > CHUNK_SIZE:
                    if current_chunk:
                        chunks.append({
                            "chunk_id": chunk_id,
                            "page": page_num,
                            "text": current_chunk.strip(),
                        })
                        chunk_id += 1
                        # Overlap: keep last N words
                        words = current_chunk.split()
                        current_chunk = " ".join(words[-CHUNK_OVERLAP:]) + " " + para
                    else:
                        current_chunk = para
                else:
                    current_chunk = (current_chunk + "\n\n" + para).strip()

            if current_chunk.strip():
                chunks.append({
                    "chunk_id": chunk_id,
                    "page": page_num,
                    "text": current_chunk.strip(),
                })
                chunk_id += 1

        return chunks

    def get_document_metadata(self, doc_id: str) -> Optional[dict]:
        meta_path = DOCUMENTS_DIR / doc_id / "metadata.json"
        if meta_path.exists():
            return json.loads(meta_path.read_text(encoding="utf-8"))
        return None

    def get_document_text(self, doc_id: str) -> Optional[str]:
        text_path = DOCUMENTS_DIR / doc_id / "full_text.txt"
        if text_path.exists():
            return text_path.read_text(encoding="utf-8")
        return None

    def get_document_pages(self, doc_id: str) -> Optional[List[dict]]:
        pages_path = DOCUMENTS_DIR / doc_id / "pages.json"
        if pages_path.exists():
            return json.loads(pages_path.read_text(encoding="utf-8"))
        return None

    def get_document_sentences(self, doc_id: str) -> Optional[List[dict]]:
        sent_path = DOCUMENTS_DIR / doc_id / "sentences.json"
        if sent_path.exists():
            return json.loads(sent_path.read_text(encoding="utf-8"))
        return None

    def get_document_pdf_path(self, doc_id: str) -> Optional[Path]:
        doc_dir = DOCUMENTS_DIR / doc_id
        if doc_dir.exists():
            for f in doc_dir.iterdir():
                if f.suffix.lower() == ".pdf":
                    return f
        return None

    def list_documents(self) -> List[dict]:
        docs = []
        if DOCUMENTS_DIR.exists():
            for d in DOCUMENTS_DIR.iterdir():
                if d.is_dir():
                    meta = self.get_document_metadata(d.name)
                    if meta:
                        docs.append(meta)
        return sorted(docs, key=lambda x: x.get("ingested_at", ""), reverse=True)

    def delete_document(self, doc_id: str) -> bool:
        doc_dir = DOCUMENTS_DIR / doc_id
        if doc_dir.exists():
            import shutil
            shutil.rmtree(doc_dir)
            return True
        return False

    def render_page_layout(self, doc_id: str, page_num: int) -> Optional[bytes]:
        """Render a specific PDF page as an image with bounding boxes drawn over sentences/words."""
        pdf_path = self.get_document_pdf_path(doc_id)
        if not pdf_path or not pdf_path.exists():
            return None

        # Load sentence rects
        sentences = self.get_document_sentences(doc_id) or []
        page_rects = []
        for s in sentences:
            if s.get("page") == page_num:
                page_rects.extend(s.get("rects", []))

        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(pdf_path))
            if page_num < 1 or page_num > len(doc):
                return None
            
            page = doc[page_num - 1]
            
            # Draw rects using fitz
            for r in page_rects:
                # r is [x0, top, x1, bottom]
                rect = fitz.Rect(r[0], r[1], r[2], r[3])
                page.draw_rect(rect, color=(1, 0, 0), width=1.5)
            
            # Render page to pixmap
            pix = page.get_pixmap(dpi=150)
            return pix.tobytes("png")
        except Exception as e:
            print(f"[PDFService] Render layout error: {e}")
            return None


pdf_service = PDFService()
