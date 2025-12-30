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
    description="REST API for Finance Consolidator - manage transactions, categories, and more (SQLite backend with optional Google Sheets export)",
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
            "Dashboard",
            "Google Sheets Export"
        ]
    }

# Import and include routers
try:
    from backend.api import transactions, dashboard, files, categories, rules, settings, export
    print("[OK] All routers imported successfully")

    app.include_router(transactions.router, prefix="/api/v1", tags=["transactions"])
    print("[OK] Registered transactions router")

    app.include_router(dashboard.router, prefix="/api/v1", tags=["dashboard"])
    print("[OK] Registered dashboard router")

    app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
    print("[OK] Registered files router")

    app.include_router(categories.router, prefix="/api/v1/categories", tags=["categories"])
    print("[OK] Registered categories router")

    app.include_router(rules.router, prefix="/api/v1/rules", tags=["rules"])
    print("[OK] Registered rules router")

    app.include_router(settings.router, prefix="/api/v1/settings", tags=["settings"])
    print("[OK] Registered settings router")

    app.include_router(export.router, prefix="/api/v1", tags=["export"])
    print("[OK] Registered export router")

except Exception as e:
    print(f"[ERROR] loading routers: {e}")
    import traceback
    traceback.print_exc()

# Serve static files (Svelte frontend) from /backend/static if it exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
