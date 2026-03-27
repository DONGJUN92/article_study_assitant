import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from lightrag import LightRAG
    from lightrag.llm.ollama import ollama_model_complete, ollama_embed
    from lightrag.utils import EmbeddingFunc
    import asyncio
    import numpy as np

    async def test():
        async def embed_wrapper(texts: list[str]) -> np.ndarray:
            return await ollama_embed(texts, embed_model="nomic-embed-text")

        rag = LightRAG(
            working_dir="./data/test_rag",
            llm_model_func=ollama_model_complete,
            llm_model_name="gemma3:4b",
            llm_model_max_async=2,
            embedding_func=EmbeddingFunc(
                embedding_dim=768,
                max_token_size=8192,
                func=embed_wrapper
            ),
        )
        print("Success!")

    asyncio.run(test())
except Exception as e:
    import traceback
    traceback.print_exc()
