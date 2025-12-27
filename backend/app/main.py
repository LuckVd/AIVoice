from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from .core.config import settings
from .core.database import engine, Base
from .api.tts import router as tts_router
from .api.saved_audios import router as saved_audios_router
from .core.celery_app import celery_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create database tables
    Base.metadata.create_all(bind=engine)

    # Create storage directories
    os.makedirs(f"{settings.storage_path}/uploads", exist_ok=True)
    os.makedirs(f"{settings.storage_path}/audio", exist_ok=True)
    os.makedirs(f"{settings.storage_path}/temp", exist_ok=True)
    os.makedirs(f"{settings.storage_path}/saved", exist_ok=True)

    yield

    # Shutdown: Cleanup if needed
    pass


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="AI Voice Text-to-Speech API",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tts_router, prefix="/api")
app.include_router(saved_audios_router, prefix="/api")

# Serve static files
if os.path.exists(settings.storage_path):
    app.mount("/storage", StaticFiles(directory=settings.storage_path), name="storage")


@app.get("/app")
async def serve_frontend():
    """Serve the main frontend application"""
    index_file = os.path.join(settings.storage_path, "index.html")
    if os.path.exists(index_file):
        from fastapi.responses import HTMLResponse
        with open(index_file, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    else:
        raise HTTPException(status_code=404, detail="Frontend not found")


@app.get("/")
async def root():
    return {
        "message": "AI Voice TTS API",
        "version": settings.version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Celery connection
        celery_app.inspect().stats()
        celery_status = "healthy"
    except Exception:
        celery_status = "unhealthy"

    return {
        "status": "healthy",
        "celery": celery_status,
        "storage": "mounted" if os.path.exists(settings.storage_path) else "missing"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)