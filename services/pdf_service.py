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
from langdetect import detect

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
        sent_regex = re.compile(r'[^.!?]+[.!?]+(?:\s|$)')
        
        title = filename.replace(".pdf", "")

        with pdfplumber.open(str(pdf_path)) as pdf:
            page_count = len(pdf.pages)
            pdf_metadata = pdf.metadata or {}
            
            if pdf_metadata.get("Title"):
                # Clean up PDF literal strings if present
                raw_title = str(pdf_metadata.get("Title", "")).strip(" ()'")
                if len(raw_title) > 5:
                    title = raw_title
                    
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                words = page.extract_words(keep_blank_chars=False)
                if not words:
                    continue
                
                # Reconstruct full text for this page
                page_text = " ".join([w["text"] for w in words])
                pages.append({
                    "page": page_num,
                    "text": page_text
                })
                full_text_parts.append(page_text)
                
                # Break into sentences
                sentences = [m.group().strip() for m in sent_regex.finditer(page_text) if m.group().strip()]
                if not sentences and page_text:
                    sentences = [page_text.strip()]
                    
                word_idx = 0
                num_words = len(words)
                
                for sent in sentences:
                    sent_stripped = re.sub(r'\W', '', sent)
                    target_len = len(sent_stripped)
                    consumed_len = 0
                    rects = []
                    
                    while word_idx < num_words and consumed_len < target_len:
                        w = words[word_idx]
                        # pdfplumber rect is [x0, top, x1, bottom] (points)
                        rects.append([w["x0"], w["top"], w["x1"], w["bottom"]])
                        w_text = str(w.get("text", ""))
                        consumed_len += len(re.sub(r'\W', '', w_text))
                        word_idx += 1
                        
                    sentence_map.append({
                        "page": page_num,
                        "text": sent,
                        "rects": rects
                    })

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


pdf_service = PDFService()
