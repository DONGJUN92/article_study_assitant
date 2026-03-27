"""Ollama LLM service for Gemma3:4b communication."""
from __future__ import annotations

import json
from typing import AsyncIterator, List, Optional, Union, Any

import httpx

from config import OLLAMA_BASE_URL, OLLAMA_MODEL


class LLMService:
    """Communicate with Ollama API for text and vision tasks."""

    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL

    async def check_health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    async def generate(
        self,
        prompt: str,
        system: str = "",
        images: Optional[List[str]] = None,
        stream: bool = False,
    ) -> Union[str, AsyncIterator[str]]:
        """Generate a response from Ollama. Returns full text or async iterator."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
        }
        if system:
            payload["system"] = system
        if images:
            payload["images"] = images  # list of base64 strings

        if stream:
            return self._stream_generate(payload)
        else:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=120,
                )
                resp.raise_for_status()
                return resp.json().get("response", "")

    async def _stream_generate(self, payload: dict) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120,
            ) as resp:
                async for line in resp.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            token = data.get("response", "")
                            if token:
                                yield token
                            if data.get("done", False):
                                return
                        except json.JSONDecodeError:
                            continue

    def _clean_text(self, text: str) -> str:
        """Programmatically strip unwanted markdown and quotes."""
        import re
        text = text.strip()
        # Remove bold markers
        text = text.replace("**", "")
        # Remove headers
        text = text.replace("###", "")
        # Remove code blocks if they exist completely wrapping the text
        if text.startswith("```") and text.endswith("```"):
            lines = text.split("\n")
            if len(lines) >= 3:
                text = "\n".join(lines[1:-1]).strip()
            else:
                text = text.replace("```", "").strip()
        # Remove markdown ticks
        text = text.replace("`", "")
        # Remove surrounding quotes if present
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1].strip()
        return text

    def _is_language_sufficient(self, text: str, target_lang: str = "ko", min_ratio: float = 0.2) -> bool:
        """Check if the text contains a sufficient ratio of characters for the target language (ko or en)."""
        import re
        # Remove whitespaces for counting
        text_no_space = re.sub(r'\s+', '', text)
        if not text_no_space:
            return True # Empty string passes
        
        # Determine target language code
        is_ko = target_lang.lower() in ["ko", "korean", "한국어"]
        
        if is_ko:
            # Count Korean characters (Hangul Syllables: 가-힣)
            korean_chars = len(re.findall(r'[가-힣]', text_no_space))
            eng_num_chars = len(re.findall(r'[A-Za-z0-9]', text_no_space))
            total_relevant = korean_chars + eng_num_chars
            if total_relevant == 0:
                return True
            return (korean_chars / total_relevant) >= min_ratio
        else:
            # For English, we expect mostly English letters and numbers, but less non-English symbols
            eng_chars = len(re.findall(r'[A-Za-z0-9]', text_no_space))
            other_chars = len(re.findall(r'[^A-Za-z0-9\s.,!?;:\'\"-]', text_no_space))
            total_relevant = eng_chars + other_chars
            if total_relevant == 0:
                return True
            return (eng_chars / total_relevant) >= 0.8

    async def generate_with_validation(
        self,
        prompt: str,
        system: str = "",
        max_retries: int = 2,
        forbid_json_and_require_numbers: bool = False,
        require_vocab_format: bool = False,
        target_lang: str = "ko"
    ) -> str:
        """Rule-based validation for structural tasks (Briefings)."""
        for attempt in range(max_retries + 1):
            res = await self.generate(prompt=prompt, system=system)
            if isinstance(res, AsyncIterator):
                candidate = ""
                async for chunk in res:
                    candidate += chunk
            else:
                candidate = res

            candidate = self._clean_text(candidate)

            is_json_failure = False
            is_numbering_failure = False
            is_vocab_failure = False
            is_language_failure = not self._is_language_sufficient(candidate, target_lang=target_lang)
            
            if forbid_json_and_require_numbers:
                if "json" in candidate.lower() or "{" in candidate or "[" in candidate:
                    is_json_failure = True
                if not ("1." in candidate and "2." in candidate and "3." in candidate):
                    is_numbering_failure = True

            if require_vocab_format:
                if "1. 일반적 의미" not in candidate or "2. 문맥적 의미" not in candidate:
                    is_vocab_failure = True

            if is_json_failure or is_numbering_failure or is_vocab_failure or is_language_failure:
                if attempt < max_retries:
                    print(f"[LLM Harness] Reject (Attempt {attempt+1}). Lang fail: {is_language_failure} ({target_lang}). JSON: {is_json_failure}. Number: {is_numbering_failure}. Vocab: {is_vocab_failure}.")
                    err_msg = "[Previous attempt failed constraints:"
                    if is_language_failure:
                        lang_name = "Korean (한국어)" if target_lang.lower() in ["ko", "korean"] else "English (영어)"
                        err_msg += f" MUST be written in {lang_name}."
                    if is_json_failure:
                        err_msg += " DO NOT use JSON, brackets, or the word 'json'."
                    if is_numbering_failure:
                        err_msg += " MUST format exactly as '1. ', '2. ', '3. '."
                    if is_vocab_failure:
                        err_msg += " MUST include exactly '1. 일반적 의미' and '2. 문맥적 의미'."
                    err_msg += " Please regenerate strictly following these rules.]"
                    prompt += f"\n\n{err_msg}"
                    continue
            return candidate
        return candidate

    async def chat(self, messages: List[dict], system: str = "", stream: bool = False, model: str = None) -> Union[str, AsyncIterator[str]]:
        """Core chat method that calls Ollama."""
        payload = {
            "model": model or self.model,
            "messages": messages,
            "system": system,
            "stream": stream,
        }
        if stream:
            return self._stream_chat(payload)
        else:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=120,
                )
                resp.raise_for_status()
                return resp.json().get("message", {}).get("content", "")

    async def _stream_chat(self, payload: dict) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120,
            ) as resp:
                async for line in resp.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            token = data.get("message", {}).get("content", "")
                            if token:
                                yield token
                            if data.get("done", False):
                                return
                        except json.JSONDecodeError:
                            continue

    async def chat_with_validation(
        self,
        messages: List[dict],
        system: str = "",
        max_retries: int = 2,
        target_lang: str = "ko"
    ) -> str:
        """Chat completion with Rule-based Validation Harness (Strict)."""
        current_messages = [msg.copy() for msg in messages]
        for attempt in range(max_retries + 1):
            res = await self.chat(messages=current_messages, system=system, stream=False)
            
            if isinstance(res, AsyncIterator):
                candidate = ""
                async for chunk in res:
                    candidate += chunk
            else:
                candidate = res

            candidate = self._clean_text(candidate)
            is_language_failure = not self._is_language_sufficient(candidate, target_lang=target_lang)

            if is_language_failure:
                if attempt < max_retries:
                    print(f"[LLM Chat Harness] Language reject (Attempt {attempt+1}, lang={target_lang}).")
                    lang_name = "Korean (한국어)" if target_lang.lower() in ["ko", "korean"] else "English (영어)"
                    current_messages.append({"role": "assistant", "content": candidate})
                    directive = (
                        f"[SYSTEM DIRECTIVE] Your previous response was rejected because it was not in {lang_name}. "
                        f"You MUST rewrite your original intended answer entirely in {lang_name}. "
                        "DO NOT apologize. DO NOT mention this rule. Just output the translated/corrected answer directly."
                    )
                    current_messages.append({"role": "user", "content": directive})
                    continue
            return candidate
        return candidate

    async def chat_with_llm_reflection(
        self,
        messages: List[dict],
        system: str = "",
        max_retries: int = 2,
        target_lang: str = "ko"
    ) -> str:
        """Chat completion with LLM-based Self-Reflection (More natural choice for Chat)."""
        current_messages = [msg.copy() for msg in messages]
        for attempt in range(max_retries + 1):
            res = await self.chat(messages=current_messages, system=system, stream=False)
            if isinstance(res, AsyncIterator):
                candidate = ""
                async for chunk in res:
                    candidate += chunk
            else:
                candidate = res
            
            candidate = candidate.strip().strip('"').strip("'")

            is_ko = target_lang.lower() in ["ko", "korean", "한국어"]
            lang_name = "Korean (한국어)" if is_ko else "English (영어)"
            
            # 1. Programmatic Checks (Fast)
            fail_reasons = []
            if len(candidate) > 500:
                fail_reasons.append("Answer exceeds 500 characters")
            if "**" in candidate:
                fail_reasons.append("Unnecessary punctuation '**' detected")
            if ' "' in candidate or '" ' in candidate or candidate.count('"') >= 2:
                 # Only fail if it looks like unnecessary quotes, not a single apostrophe
                fail_reasons.append("Unnecessary punctuation '\"\"' detected")
            
            # 2. LLM Reflection (Nuanced)
            reflection_prompt = f"""Evaluate this AI response for a research paper assistant.
Response: "{candidate}"

[CRITERIA]
1. Is it written at least 70% in {lang_name}? (English terminology is allowed) (T/F)
2. Does it avoid unnecessary punctuation like ** or ""? (T/F)
3. Is it under 500 chars and accurately reflects the paper context? (T/F)

If ALL are T, output 'PASS'.
If any are F, output 'FAIL: [Reason]'.
"""
            reflection_res = await self.chat(
                messages=[{"role": "user", "content": reflection_prompt}],
                system="You are a strict quality controller. Output only PASS or FAIL with reason.",
                stream=False,
                model="gemma3:1b"
            )
            
            reflection_text = (reflection_res if isinstance(reflection_res, str) else "").strip()
            
            if not fail_reasons and "PASS" in reflection_text.upper():
                return candidate
            else:
                if attempt < max_retries:
                    llm_reason = reflection_text.replace("FAIL:", "").strip() if "FAIL" in reflection_text.upper() else ""
                    all_reasons = "; ".join(fail_reasons)
                    if llm_reason:
                        all_reasons = f"{all_reasons}; {llm_reason}" if all_reasons else llm_reason
                    
                    print(f"[LLM Reflection] Reject (Attempt {attempt+1}). Reasons: {all_reasons}")
                    
                    current_messages.append({"role": "assistant", "content": candidate})
                    directive = (
                        f"[SYSTEM DIRECTIVE] Your previous response was rejected for: {all_reasons}. "
                        f"Please rewrite a natural, helpful answer in {lang_name} that is under 500 characters and "
                        "avoids formatting like ** or \"\"."
                    )
                    current_messages.append({"role": "user", "content": directive})
                    continue
        return candidate


llm_service = LLMService()
