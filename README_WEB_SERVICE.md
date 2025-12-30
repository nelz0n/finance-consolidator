# Finance Consolidator - Web Service

Transform your Finance Consolidator into a modern web application with a Sonarr-like interface.

## Quick Start

### 1. Install Dependencies

```bash
# Backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

### 2. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your GEMINI_API_KEY
```

### 3. Initialize Database

```bash
# Create database and migrate existing Google Sheets data
python scripts/migrate_to_sqlite.py
```

### 4. Run Development Server

**Option A: Separate Backend & Frontend (Development)**

```bash
# Terminal 1: Backend
uvicorn backend.app:app --reload --port 8080

# Terminal 2: Frontend
cd frontend
npm run dev
```

Access at: http://localhost:5173

**Option B: Docker (Production)**

```bash
# Build and run
cd docker
docker-compose up --build

# Run in background
docker-compose up -d
```

Access at: http://localhost:8080

## Features

### ✅ Implemented

- **Backend API (FastAPI)**
  - RESTful API with auto-generated docs at `/api/docs`
  - Transaction CRUD operations with filtering
  - Dashboard summary statistics
  - SQLite database with migrations
  - Reuses existing CLI code (parser, normalizer, categorizer)

- **Frontend (Svelte)**
  - Modern single-page application
  - Dashboard with income/expense cards
  - Transaction browser with table view
  - API client for backend communication

- **Docker**
  - Multi-stage build (Svelte → Python)
  - Single container deployment
  - Volume mounts for data persistence
  - Health checks

### 🚧 To Be Implemented

Phase 2-4 features (can be added incrementally):
- Category management UI
- Rule editor
- File upload interface
- Charts and visualizations (Chart.js)
- Advanced filtering and search
- Google Sheets sync

## Architecture

```
┌─────────────────────────────────────┐
│   Frontend (Svelte SPA)             │
│   - Dashboard                       │
│   - Transaction Browser             │
│   Port: 5173 (dev) / 8080 (prod)    │
└────────────────┬────────────────────┘
                 │ REST API (JSON)
┌────────────────▼────────────────────┐
│   Backend (FastAPI)                 │
│   - Transactions API                │
│   - Dashboard API                   │
│   - Reuses src/ code                │
│   Port: 8080                        │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│   Data Layer                        │
│   - SQLite (data/finance.db)        │
│   - Google Sheets (backup)          │
└─────────────────────────────────────┘
```

## API Endpoints

### Transactions

- `GET /api/v1/transactions` - List with filtering & pagination
- `GET /api/v1/transactions/{id}` - Get single transaction
- `PUT /api/v1/transactions/{id}` - Update transaction
- `DELETE /api/v1/transactions/{id}` - Delete transaction
- `GET /api/v1/transactions/uncategorized/list` - Get uncategorized

### Dashboard

- `GET /api/v1/dashboard/summary` - Summary statistics

### System

- `GET /api/v1/health` - Health check

Full API documentation: http://localhost:8080/api/docs

## Database Schema

Core tables:
- `transactions` - All financial transactions (22 columns)
- `accounts` - Bank accounts
- `institutions` - Financial institutions (ČSOB, Partners, Wise)
- `owners` - Account owners
- `categories` - 3-tier category hierarchy
- `categorization_rules` - Manual rules
- `import_jobs` - File processing status
- `sync_log` - Google Sheets sync history

## Migration from CLI

The web service is **fully backward compatible** with the existing CLI:

1. **CLI still works** - All existing `python -m src.main` commands work unchanged
2. **Dual data stores** - Data can exist in both Google Sheets and SQLite
3. **One-time migration** - Run `scripts/migrate_to_sqlite.py` to import existing data
4. **Optional sync** - Enable bidirectional sync between SQLite ↔ Google Sheets

## Directory Structure

```
finance-consolidator/
├── backend/                 # FastAPI application
│   ├── api/                 # REST API endpoints
│   ├── database/            # SQLAlchemy models & repos
│   ├── schemas/             # Pydantic models
│   ├── services/            # Business logic
│   └── app.py               # FastAPI entry point
│
├── frontend/                # Svelte application
│   ├── src/
│   │   ├── components/      # Svelte components
│   │   ├── routes/          # Page components
│   │   └── lib/             # Utilities (API client)
│   └── package.json
│
├── docker/                  # Docker configuration
│   ├── Dockerfile           # Multi-stage build
│   └── docker-compose.yml   # Container orchestration
│
├── src/                     # Existing CLI code (reused)
│   ├── core/                # Parser, normalizer, writer
│   ├── utils/               # Categorizer, currency
│   └── connectors/          # Google Drive/Sheets
│
├── scripts/
│   └── migrate_to_sqlite.py # Migration script
│
└── data/
    ├── finance.db           # SQLite database
    ├── uploads/             # Uploaded files
    └── logs/                # Application logs
```

## Development

### Run Backend Only

```bash
uvicorn backend.app:app --reload --port 8080
```

### Run Frontend Only

```bash
cd frontend
npm run dev
```

### Build Frontend for Production

```bash
cd frontend
npm run build
# Output: backend/static/
```

### Run Tests

```bash
# Backend tests
pytest tests/

# Frontend tests
cd frontend
npm run test
```

## Deployment on NAS

### Docker Compose

1. Copy files to NAS:
```bash
scp -r finance-consolidator/ nas:/volume1/docker/
```

2. SSH into NAS and run:
```bash
cd /volume1/docker/finance-consolidator/docker
docker-compose up -d
```

3. Access web UI:
```
http://nas-ip:8080
```

### Volume Structure

```
/volume1/docker/finance-consolidator/
├── docker-compose.yml
├── .env
└── data/
    ├── finance.db          # SQLite database
    ├── uploads/            # Uploaded files
    ├── logs/               # Application logs
    └── credentials/        # Google OAuth
```

## Troubleshooting

### Backend won't start

Check logs:
```bash
docker-compose logs -f finance-consolidator
```

Common issues:
- Missing .env file → Copy from .env.example
- Database not initialized → Run migration script
- Port 8080 already in use → Change port in docker-compose.yml

### Frontend can't connect to backend

In development mode, frontend (port 5173) proxies to backend (port 8080).
Ensure backend is running:
```bash
curl http://localhost:8080/api/v1/health
```

### Migration failed

Check Google Sheets authentication:
- Ensure credentials exist in data/credentials/
- Run CLI once to authenticate: `python -m src.main --dry-run`
- Then re-run migration

## Next Steps

1. **Phase 2**: Add category management and rule editor UI
2. **Phase 3**: Add file upload and processing interface
3. **Phase 4**: Add charts and visualizations
4. **Phase 5**: Add Google Sheets sync service

See `C:\Users\bbarl\.claude\plans\abstract-coalescing-wombat.md` for full implementation plan.

## Support

- API Docs: http://localhost:8080/api/docs
- Issues: Create an issue in the repository
- Logs: `data/logs/finance_consolidator.log`
