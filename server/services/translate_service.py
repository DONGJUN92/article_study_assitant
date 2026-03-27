"""Translation service using Argos Translate (offline)."""
from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import List, Optional, Tuple

from config import DEFAULT_TARGET_LANG


class TranslateService:
    """Offline translation using argostranslate."""

    def __init__(self):
        self._initialized = False
        self._lock = asyncio.Lock()

    async def _ensure_init(self):
        if self._initialized:
            return
        async with self._lock:
            if self._initialized:
                return
            try:
                import argostranslate.package
                import argostranslate.translate
                argostranslate.package.update_package_index()
                self._initialized = True
            except Exception as e:
                print(f"[Translate] Init failed: {e}")
                self._initialized = True  # Don't retry

    def _get_installed_languages(self) -> list:
        try:
            import argostranslate.translate
            return argostranslate.translate.get_installed_languages()
        except Exception:
            return []

    def _install_package(self, from_code: str, to_code: str) -> bool:
        """Install translation package if not already installed."""
        try:
            import argostranslate.package
            import argostranslate.translate

            available = argostranslate.package.get_available_packages()
            pkg = next(
                (p for p in available
                 if p.from_code == from_code and p.to_code == to_code),
                None,
            )
            if pkg:
                argostranslate.package.install_from_path(pkg.download())
                return True
            return False
        except Exception as e:
            print(f"[Translate] Package install error: {e}")
            return False

    async def translate_text(
        self,
        text: str,
        from_lang: str = "en",
        to_lang: str = DEFAULT_TARGET_LANG,
    ) -> str:
        """High-quality translation using Ollama LLM."""
        # For academic papers, LLM provides much better context than argostranslate
        return await self._translate_via_llm(text, from_lang, to_lang)

    async def _translate_via_llm(
        self, text: str, from_lang: str, to_lang: str
    ) -> str:
        """Fallback: use Ollama LLM for translation."""
        from services.llm_service import llm_service

        lang_names = {
            "ko": "Korean", "en": "English", "ja": "Japanese",
            "zh": "Chinese", "de": "German", "fr": "French",
            "es": "Spanish",
        }
        to_name = lang_names.get(to_lang, to_lang)
        from_name = lang_names.get(from_lang, from_lang)

        system_prompt = f"You are an expert translator specializing in translating {from_name} academic texts to {to_name}."
        prompt = (
            f"Please translate the following {from_name} text into natural {to_name}.\n"
            f"Provide ONLY the {to_name} translation. Do not include the original text, markdown blocks, or any explanations.\n\n"
            f"Text to translate:\n{text}"
        )
        result = await llm_service.generate(prompt=prompt, system=system_prompt)
        
        # Clean up possible markdown or quotes that the small model might output
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            cleaned = cleaned.rsplit("```", 1)[0].strip()
        
        return cleaned

    async def translate_paragraphs(
        self,
        paragraphs: List[str],
        from_lang: str = "en",
        to_lang: str = DEFAULT_TARGET_LANG,
    ):
        """Generator that yields (index, original, translated) tuples."""
        for i, para in enumerate(paragraphs):
            if not para.strip():
                yield i, para, para
                continue
            translated = await self.translate_text(para, from_lang, to_lang)
            yield i, para, translated


translate_service = TranslateService()
