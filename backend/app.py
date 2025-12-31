"""FastAPI Application Entry Point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import logging
from pathlib import Path

# Set up logging to file
log_dir = Path("data/logs")
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "finance_consolidator.log"

# Configure root logger to write to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"Logging initialized. Log file: {log_file}")

# Create FastAPI app
app = FastAPI(
    title="Finance Consolidator API",
    description="REST API for Finance Consolidator - manage transactions, categories, and more (SQLite backend)",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "backend": "SQLite",
        "features": [
            "File Upload & Processing",
            "Transaction Browser",
            "Category Management",
            "Rules Editor",
            "Dashboard"
        ]
    }

# Import and include routers
try:
    from backend.api import transactions, dashboard, files, categories, rules, settings, accounts
    logger.info("[OK] All routers imported successfully")

    app.include_router(transactions.router, prefix="/api/v1", tags=["transactions"])
    logger.info("[OK] Registered transactions router")

    app.include_router(dashboard.router, prefix="/api/v1", tags=["dashboard"])
    logger.info("[OK] Registered dashboard router")

    app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
    logger.info("[OK] Registered files router")

    app.include_router(categories.router, prefix="/api/v1/categories", tags=["categories"])
    logger.info("[OK] Registered categories router")

    app.include_router(rules.router, prefix="/api/v1/rules", tags=["rules"])
    logger.info("[OK] Registered rules router")

    app.include_router(settings.router, prefix="/api/v1/settings", tags=["settings"])
    logger.info("[OK] Registered settings router")

    app.include_router(accounts.router, prefix="/api/v1", tags=["accounts"])
    logger.info("[OK] Registered accounts router")

except Exception as e:
    logger.error(f"[ERROR] loading routers: {e}")
    import traceback
    traceback.print_exc()

# Serve static files (Svelte frontend)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    from fastapi.responses import FileResponse
    from fastapi import HTTPException

    # Mount assets directory if it exists (Vite output)
    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # Serve index.html at root
    @app.get("/")
    async def serve_root():
        return FileResponse(static_dir / "index.html")

    # Catch-all for SPA routing (must be defined last)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # API 404s should return JSON, not HTML
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
            
        # Check if file exists in static directory (e.g. favicon.ico, manifest.json)
        possible_file = static_dir / full_path
        if possible_file.is_file():
            return FileResponse(possible_file)
            
        # Fallback to index.html for unknown routes (SPA History API)
        return FileResponse(static_dir / "index.html")
