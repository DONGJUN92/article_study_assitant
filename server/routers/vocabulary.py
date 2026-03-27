"""Vocabulary router — smart word book with spaced repetition."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from models.schemas import VocabEntry
from config import VOCAB_DIR
from services.llm_service import llm_service

router = APIRouter(prefix="/api", tags=["vocabulary"])

VOCAB_FILE = VOCAB_DIR / "vocabulary.json"


def _load_vocab() -> List[dict]:
    if VOCAB_FILE.exists():
        return json.loads(VOCAB_FILE.read_text(encoding="utf-8"))
    return []


def _save_vocab(entries: List[dict]):
    VOCAB_FILE.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )


@router.get("/vocabulary", response_model=List[VocabEntry])
async def get_vocabulary(doc_id: Optional[str] = None):
    entries = _load_vocab()
    if doc_id:
        return [e for e in entries if e.get("doc_id") == doc_id]
    return entries


@router.post("/vocabulary", response_model=VocabEntry)
async def add_vocabulary(entry: VocabEntry):
    if not entry.meaning:
        try:
            prompt = f"""You are an elite academic dictionary.
Word to define: "{entry.word}"
Surrounding Context: "{entry.context_sentence or 'None'}"

Task: Provide a concise definition in two parts.
IMPORTANT RULE: YOU MUST WRITE THE OUTPUT ENTIRELY IN KOREAN (한국어).

1. [일반적 의미] The general/most common meaning in Korean.
2. [문맥적 의미] The specific meaning within the provided context in Korean.

Do not include any other text except these two lines."""
            result = await llm_service.generate_with_validation(
                prompt=prompt, 
                max_retries=2,
                require_vocab_format=True
            )
            entry.meaning = result.strip()
        except Exception as e:
            print(f"Vocab gen error: {e}")
            entry.meaning = f"(의미 자동 생성 실패: {e})"

    entries = _load_vocab()

    # Check for duplicate
    for e in entries:
        if e["word"].lower() == entry.word.lower() and e["doc_id"] == entry.doc_id:
            return VocabEntry(**e)

    new_entry = entry.model_dump()
    new_entry["added_at"] = datetime.now(timezone.utc).isoformat()

    entries.append(new_entry)
    _save_vocab(entries)
    return VocabEntry(**new_entry)


@router.delete("/vocabulary/{word}")
async def delete_word(word: str, doc_id: Optional[str] = None):
    entries = _load_vocab()
    if doc_id:
        new_entries = [e for e in entries if not (e["word"].lower() == word.lower() and e.get("doc_id") == doc_id)]
    else:
        new_entries = [e for e in entries if e["word"].lower() != word.lower()]
        
    if len(new_entries) == len(entries):
        raise HTTPException(404, "Word not found")
    _save_vocab(new_entries)
    return {"status": "deleted"}


@router.delete("/vocabulary/document/{doc_id}")
async def delete_document_vocab(doc_id: str):
    entries = _load_vocab()
    new_entries = [e for e in entries if e.get("doc_id") != doc_id]
    _save_vocab(new_entries)
    return {"status": "deleted"}


@router.get("/vocabulary/due")
async def get_due_reviews():
    """Get words due for review."""
    entries = _load_vocab()
    now = datetime.now(timezone.utc).isoformat()
    due = [e for e in entries if e.get("next_review", "") <= now]
    return due
