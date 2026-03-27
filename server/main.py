"""Article Study — FastAPI Local Backend Server."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from config import SERVER_HOST, SERVER_PORT
from models.schemas import HealthResponse
from services.llm_service import llm_service

# ── Import routers ─────────────────────────────────────
from routers import ingest, query, translate, vocabulary

# ── App ────────────────────────────────────────────────
app = FastAPI(
    title="Article Study API",
    description="Local backend for the Article Study browser extension",
    version="1.0.0",
)

# Allow extension to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"DEBUG: Received {request.method} {request.url.path}")
    response = await call_next(request)
    print(f"DEBUG: Handled {request.method} {request.url.path} -> {response.status_code}")
    return response

# ── Register routers ──────────────────────────────────
app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(translate.router)
app.include_router(vocabulary.router)


# ── Health check ──────────────────────────────────────
@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    ollama_ok = await llm_service.check_health()
    return HealthResponse(
        status="ok" if ollama_ok else "degraded",
        ollama=ollama_ok,
        rag=True,
        version="1.0.0",
    )


@app.get("/")
async def root():
    return {
        "name": "Article Study API",
        "version": "1.0.0",
        "docs": "/docs",
    }


# ── Run ───────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Article Study server starting on http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"📖 API docs: http://{SERVER_HOST}:{SERVER_PORT}/docs")
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
