from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.database import Base, engine
import backend.models  # Ensure all SQLAlchemy models are registered
from backend.logging_config import setup_logging, RealtimeRequestLoggingMiddleware
from backend.routers import (
    transitions_router,
    documents_router,
    profile_router,
    knowledge_router,
    kt_levels_router,
    stakeholders_router,
    availability_router,
    scheduling_router,
    governance_router,
    export_router,
    database_gateway_router,
    modules_router,
)

# Setup real-time terminal logger (auto-detects -v for DEBUG)
logger = setup_logging()

# Initialize database schema
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="KT Planner - Master Orchestration Platform",
    version="1.0.0",
    description="AI-powered Transition Planning & Knowledge Transfer Orchestration Platform",
)

# Real-time request logging middleware
app.add_middleware(RealtimeRequestLoggingMiddleware)

# CORS middleware for local frontend dev server & production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(transitions_router)
app.include_router(documents_router)
app.include_router(profile_router)
app.include_router(knowledge_router)
app.include_router(kt_levels_router)
app.include_router(stakeholders_router)
app.include_router(availability_router)
app.include_router(scheduling_router)
app.include_router(governance_router)
app.include_router(export_router)
app.include_router(database_gateway_router)
app.include_router(modules_router)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "KT Planner Master Backend",
        "version": "1.0.0",
        "authoritative_db": "SQLite kt_planner.db",
    }

# Single Deployable Service: Serve static frontend files if built
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = FRONTEND_DIST / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")

