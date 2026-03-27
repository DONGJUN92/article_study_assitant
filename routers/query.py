"""Query router — word analysis, sentence translation, and RAG chat."""
from __future__ import annotations

import json
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from models.schemas import (
    WordRequest, WordResponse, WordExample,
    SentenceRequest, SentenceResponse,
    ChatRequest, ChatMessage,
    BriefingResponse,
)
from services.llm_service import llm_service
from services.rag_service import rag_service
from services.pdf_service import pdf_service

router = APIRouter(prefix="/api", tags=["query"])

SYSTEM_PROMPT = (
    "You are an expert research paper analysis AI. "
    "You must strictly base your answers on the provided Deep Knowledge Context (RAG). "
    "If the answer is not in the context, state that clearly. "
    "Keep answers concise, accurate, and always in the user's language."
)


@router.post("/word", response_model=WordResponse)
async def analyze_word(req: WordRequest):
    """Contextual word analysis using LLM + RAG."""
    try:
        # Get RAG context for the word
        rag_context = await rag_service.query(
            req.doc_id,
            f"The word '{req.word}' in context: {req.context}"
        )

        prompt = f"""You are an expert academic linguist. Analyze the exact meaning of the word "{req.word}" strictly within this paper's context.

Context sentence: {req.context}

Deep Knowledge Context (RAG):
{rag_context[:3000]}

Return your analysis as JSON with these exact keys. Be concise.
{{
  "contextual_meaning": "Korean meaning of the word exactly as used in this paper's context",
  "academic_meaning": "General academic/technical meaning in Korean",
  "synonyms": ["synonym1", "synonym2"],
  "antonyms": ["antonym1"],
  "pronunciation": "IPA pronunciation",
  "examples": [{{"sentence": "short example sentence from the context", "page": null}}]
}}

Output ONLY valid JSON, nothing else."""

        result = await llm_service.generate_with_validation(prompt=prompt, max_retries=2)

        # Parse JSON from response
        try:
            # Clean potential markdown wrapping
            cleaned = result.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            data = {
                "contextual_meaning": result,
                "academic_meaning": "",
                "synonyms": [],
                "antonyms": [],
                "pronunciation": "",
                "examples": [],
            }

        return WordResponse(
            word=req.word,
            contextual_meaning=data.get("contextual_meaning", ""),
            academic_meaning=data.get("academic_meaning", ""),
            synonyms=data.get("synonyms", []),
            antonyms=data.get("antonyms", []),
            pronunciation=data.get("pronunciation", ""),
            examples=[
                WordExample(sentence=e.get("sentence", ""), page=e.get("page"))
                for e in data.get("examples", [])
            ],
        )
    except Exception as e:
        raise HTTPException(500, f"Word analysis failed: {e}")


@router.post("/sentence", response_model=SentenceResponse)
async def analyze_sentence(req: SentenceRequest):
    """Translate sentence + provide 3-line context summary using RAG."""
    try:
        # Get paper context
        rag_context = await rag_service.query(req.doc_id, req.sentence)

        prompt = f"""You are an expert academic translator.

Selected sentence: "{req.sentence}"

Deep Knowledge Context (RAG):
{rag_context[:3000]}

Provide:
1. A natural Korean translation
2. Three short lines explaining its significance based on the Deep Knowledge Context
3. Which section it belongs to

Return as JSON:
{{
  "translation": "Korean translation",
  "summary": [
    "Contextual significance 1",
    "Contextual significance 2",
    "Contextual significance 3"
  ],
  "section": "Section name"
}}

Output ONLY valid JSON, nothing else."""

        result = await llm_service.generate_with_validation(prompt=prompt, max_retries=2)

        try:
            cleaned = result.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            data = {
                "translation": result,
                "summary": [result],
                "section": "",
            }

        return SentenceResponse(
            original=req.sentence,
            translation=data.get("translation", ""),
            summary=data.get("summary", [])[:3],
            section=data.get("section", ""),
        )
    except Exception as e:
        raise HTTPException(500, f"Sentence analysis failed: {e}")


@router.post("/chat")
async def chat_with_paper(req: ChatRequest):
    """RAG-powered chat with streaming response."""
    try:
        # Retrieve context
        rag_context = await rag_service.query(req.doc_id, req.query)
        # Fetch a bit of global context for better "sense" of the paper (similar to briefing)
        global_text = pdf_service.get_document_text(req.doc_id) or ""
        global_context = global_text[:2000]
        
        print(f"[DEBUG] Chat req: lang={getattr(req, 'language', 'N/A')}, query='{req.query}'")
        print(f"[DEBUG] RAG context length: {len(rag_context)}")

        # Build messages
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": f"GLOBAL PAPER OVERVIEW:\n{global_context}"},
            {"role": "system", "content": f"DEEP KNOWLEDGE CONTEXT (RAG):\n{rag_context[:4000]}"}
        ]
        
        # The frontend appends the current query to req.history before sending.
        # We must exclude the very last item (the raw query) from the history
        # so we can replace it with our RAG-enriched version without duplication.
        history_to_keep = req.history[-11:-1] if len(req.history) > 0 else []
        for msg in history_to_keep:
            messages.append({"role": msg.role, "content": msg.content})

        # Add the current user question at the end
        messages.append({"role": "user", "content": f"QUESTION: {req.query}"})

        # Stream response (Pseudo-streaming for validated content)
        async def generate():
            # Generate using LLM with Reflection (Selective Rollback for more natural chat)
            # Use getattr as a backup for schema desync
            target_lang = getattr(req, "language", "ko")
            result = await llm_service.chat_with_llm_reflection(
                messages=messages,
                system=SYSTEM_PROMPT,
                target_lang=target_lang
            )    
            # Simulate streaming for UX
            # We yield words to make it feel like AI is typing
            words = result.split(" ")
            for i, word in enumerate(words):
                # Add space back except for the last word
                token = word + (" " if i < len(words) - 1 else "")
                yield {"event": "token", "data": token}
                
            yield {"event": "done", "data": ""}

        return EventSourceResponse(generate())

    except Exception as e:
        raise HTTPException(500, f"Chat failed: {e}")


@router.post("/briefing", response_model=BriefingResponse)
async def generate_briefing(req: dict):
    """Generate a one-click paper briefing."""
    doc_id = req.get("doc_id", "")
    language = req.get("language", "ko")
    if not doc_id:
        raise HTTPException(400, "doc_id required")

    target_lang = "Korean" if language == "ko" else "English"

    try:
        full_text = pdf_service.get_document_text(doc_id)
        if not full_text:
            raise HTTPException(404, "Document not found")

        target_lang_kr = "한국어(Korean)" if target_lang == "Korean" else "영어(English)"
        
        # Define the 4 modular prompts
        p_summary = f"""You are an elite academic reviewer. Analyze the following paper context.
Knowledge Context: {full_text[:5000]}
Task: Write a highly concise, 5-line summary of the key findings, methodologies, and core contributions.
IMPORTANT constraint: You must output the response ENTIRELY in {target_lang_kr}. Do not use formatting like '*' or bold, just 5 distinct lines."""

        p_difficulty = f"""You are an elite academic reviewer. Analyze the following paper context.
Knowledge Context: {full_text[:1000]}
Task: Assess the reading difficulty. 
IMPORTANT constraint: Output ONLY ONE WORD from this list based exactly on the language {target_lang_kr}:
If Korean: "쉬움", "보통", "어려움", or "전문가용"
If English: "Easy", "Medium", "Hard", or "Expert"
Output NOTHING ELSE."""

        p_questions = f"""You are an elite academic reviewer. Analyze the following paper context.
Knowledge Context: {full_text[:3000]}
Task: Extract exactly 3 core research questions addressed by this paper.
IMPORTANT constraint: You must output the response ENTIRELY in {target_lang_kr}.
Format exactly as a numbered list starting with 1., 2., 3.
Example:
1. Question one?
2. Question two?
3. Question three?
Do NOT output anything else. No introductory text. DO NOT formulate as JSON."""

        p_guide = f"""You are an elite academic reviewer. Analyze the following paper context.
Knowledge Context: {full_text[:3000]}
Task: Write a concise reading guide (2-3 sentences) advising a student on how to approach this specific paper (e.g., "Focus on the methodology section first", or "Pay attention to table 2").
IMPORTANT constraint: You must output the response ENTIRELY in {target_lang_kr}."""

        # Execute all 4 calls concurrently through the LLM validator
        import asyncio
        summary_res, diff_res, questions_res, guide_res = await asyncio.gather(
            llm_service.generate_with_validation(prompt=p_summary, max_retries=2, target_lang=language),
            llm_service.generate_with_validation(prompt=p_difficulty, max_retries=2, target_lang=language),
            llm_service.generate_with_validation(prompt=p_questions, max_retries=2, forbid_json_and_require_numbers=True, target_lang=language),
            llm_service.generate_with_validation(prompt=p_guide, max_retries=2, target_lang=language)
        )

        # Process questions array
        key_questions = []
        try:
            q_clean = questions_res.strip()
            # Extract only lines that start with numbering
            lines = q_clean.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith(("1.", "2.", "3.")):
                    # Strip the numbering from the start: e.g. "1. This is a question" -> "This is a question"
                    clean_line = line[2:].strip()
                    if clean_line:
                        key_questions.append(clean_line)
            
            # Fallback if no strict lines matched
            if not key_questions:
                key_questions = [line.strip("- 1234567890.*") for line in lines if line.strip()][:3]
        except Exception as e:
            key_questions = ["질문 추출 실패"]

        return BriefingResponse(
            summary=summary_res.strip(),
            key_questions=key_questions[:3],
            difficulty=diff_res.strip(),
            reading_guide=guide_res.strip()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Briefing failed: {e}")
