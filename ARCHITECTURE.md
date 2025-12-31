# Architecture Documentation

This document describes the technical architecture of the Finance Consolidator application.

## System Overview

Finance Consolidator is a full-stack web application for personal finance management, consisting of:

- **Backend**: FastAPI REST API server with SQLite database
- **Frontend**: Svelte SPA with Vite build system
- **Processing Pipeline**: Configurable CSV/XLSX parser and normalizer
- **Storage**: SQLite database with SQLAlchemy ORM

```
┌─────────────┐
│   Browser   │
│  (Svelte)   │
└──────┬──────┘
       │ HTTP/JSON
       ▼
┌─────────────┐
│   FastAPI   │
│   Backend   │
└──────┬──────┘
       │
       ├──► SQLite Database
       │    (Transactions, Rules, etc.)
       │
       └──► Processing Pipeline
            (Parser → Normalizer → Categorizer → Writer)
```

## Technology Stack

### Backend
- **Framework**: FastAPI 0.104+
- **ORM**: SQLAlchemy 2.0+
- **Database**: SQLite 3
- **Validation**: Pydantic v2
- **Server**: Uvicorn (ASGI)

### Frontend
- **Framework**: Svelte 4
- **Build Tool**: Vite 5
- **HTTP Client**: Axios
- **Styling**: Custom CSS (no framework)

### Processing
- **File Parsing**: Python stdlib (csv, openpyxl)
- **Currency**: CNB API + static rates
- **AI**: Google Gemini API
- **Configuration**: PyYAML

## Architecture Layers

### 1. Frontend Layer (`frontend/`)

**Purpose**: User interface and client-side logic

**Components**:
- **Routes** (`src/routes/`): Page components
  - `Transactions.svelte`: Main transaction table with filtering, editing, bulk operations
  - `Dashboard.svelte`: Summary statistics and charts
  - `FileUpload.svelte`: Drag-and-drop file upload interface
  - `Rules.svelte`: Categorization rule management
  - `Categories.svelte`: Category hierarchy management
  - `Settings.svelte`: Application settings

- **Library** (`src/lib/`):
  - `api.js`: Axios-based API client with typed endpoints
  - Shared utilities and components

**Key Features**:
- Reactive state management (Svelte stores)
- Client-side filtering for account/type (temporary until backend support)
- LocalStorage for column preferences and ordering
- Real-time job status polling during file uploads

**Build Process**:
```
npm run dev    → Vite dev server on :5173
npm run build  → Production build to /build
```

### 2. API Layer (`backend/api/`)

**Purpose**: REST API endpoints for CRUD operations

**Routers**:

1. **`transactions.py`**: Transaction CRUD and filtering
   - `GET /transactions`: List with filters, pagination, sorting
   - `GET /transactions/{id}`: Single transaction details
   - `PUT /transactions/{id}`: Update transaction
   - `DELETE /transactions/{id}`: Delete transaction
   - `POST /transactions/reapply-rules`: Re-categorize filtered transactions
   - `GET /transactions/uncategorized/list`: List uncategorized

2. **`files.py`**: File upload and processing
   - `POST /upload`: Upload bank statement, returns job_id
   - `GET /jobs`: List recent processing jobs
   - `GET /jobs/{id}`: Get job status and logs
   - Background task processing with detailed logging

3. **`categories.py`**: Category hierarchy management
   - `GET /categories/tree`: Full 3-tier hierarchy
   - `GET /categories/tier1`: List Tier1 categories
   - `GET /categories/tier2/{tier1}`: List Tier2 for Tier1
   - `GET /categories/tier3/{tier1}/{tier2}`: List Tier3 for Tier2
   - `POST /categories/tier1`: Create new Tier1
   - `DELETE /categories/tier1/{tier1}`: Delete Tier1 and children

4. **`rules.py`**: Categorization rules
   - `GET /rules`: List all rules
   - `POST /rules`: Create new rule
   - `PUT /rules/{id}`: Update rule
   - `DELETE /rules/{id}`: Delete rule
   - `POST /rules/test`: Test rule against transaction

5. **`settings.py`**: Application settings
   - `GET /settings`: Get current settings
   - `PUT /settings`: Update settings

6. **`accounts.py`**: Account descriptions
   - `GET /accounts`: Get account descriptions map
   - `POST /accounts`: Save account descriptions
   - `PUT /accounts/{account_number}`: Update account
   - `DELETE /accounts/{account_number}`: Delete account

**Common Patterns**:
- Dependency injection for database sessions
- Pydantic schemas for request/response validation
- HTTPException for error responses
- Transaction-level database operations

### 3. Database Layer (`backend/database/`)

**Models** (`models.py`):

```python
Transaction
├── id (PK)
├── transaction_id (unique hash)
├── date, amount, currency
├── amount_czk, exchange_rate
├── description
├── category_tier1, tier2, tier3
├── categorization_source, ai_confidence
├── owner_id (FK), institution_id (FK), account_id (FK)
├── counterparty info
├── czech banking symbols
└── metadata (source_file, processed_date)

Institution (ČSOB, Partners, Wise)
Owner (Branislav, Mirka, etc.)
Account (283337817/0300, etc.)
Category (3-tier hierarchy)
CategorizationRule (pattern-based rules)
ImportJob (file upload tracking)
SystemSetting (key-value config)
```

**Repositories** (`repositories/`):
- `transaction_repo.py`: Transaction CRUD with complex filtering
- `category_repo.py`: Category hierarchy operations
- `rule_repo.py`: Rule management

**Key Features**:
- Composite indexes for fast queries
- Foreign key relationships with cascading
- Duplicate detection via transaction_id hash
- Efficient bulk operations

### 4. Processing Pipeline (`src/core/`)

**Flow**:
```
Upload → Parse → Normalize → Categorize → Write → Database
```

**Components**:

1. **FileParser** (`parser.py`)
   - Auto-detects institution from filename
   - Loads appropriate YAML configuration
   - Handles CSV and XLSX formats
   - Applies transformations (concatenate, strip, replace, split)
   - Returns list of raw transaction dictionaries

2. **DataNormalizer** (`normalizer.py`)
   - Converts raw dicts to Transaction objects
   - Parses dates (multiple formats supported)
   - Parses amounts (various decimal/thousands separators)
   - Converts currencies to CZK using CNB API or static rates
   - Calculates exchange rates
   - Generates unique transaction IDs (hash-based)
   - Handles institution-specific quirks

3. **TransactionCategorizer** (`src/utils/categorizer.py`)
   - **Stage 1**: Check for internal transfers (account-to-account)
   - **Stage 2**: Apply manual rules (priority-ordered pattern matching)
   - **Stage 3**: AI fallback (Gemini API with rate limiting)
   - Returns: tier1, tier2, tier3, owner, is_internal, source, confidence

4. **DatabaseWriter** (`database_writer.py`)
   - Bulk writes to SQLite
   - Modes: append (skip duplicates) or overwrite (update existing)
   - Creates institutions, owners, accounts on-the-fly
   - Transaction-level error handling
   - Returns statistics: added, updated, skipped

**Configuration-Driven**:
All institution-specific logic is in YAML files, not code:

```yaml
# config/institutions/csob.yaml
institution:
  name: "ČSOB"
  code: "csob"

file_detection:
  filename_patterns: ["csob_*.csv", "CSOB_*.csv"]

csv_format:
  encoding: "utf-8-sig"  # BOM
  delimiter: ";"
  skip_rows: 2
  has_header: true

column_mapping:
  date: "Datum"
  amount: "Částka"
  currency: "Měna"
  description: "Popis"
  variable_symbol: "VS"
  # ... etc

transformations:
  date:
    format: "%d.%m.%Y"
  amount:
    decimal_separator: ","
    thousands_separator: " "

owner_detection:
  method: "account_mapping"
  account_mapping:
    "283337817/0300": "Branislav"
    "210621040/0300": "Mirka"
```

### 5. Utilities (`src/utils/`)

**CurrencyConverter** (`currency.py`):
- Primary: CNB (Czech National Bank) API for real-time rates
- Fallback: Static rates from settings.yaml
- Caches API responses (15-minute TTL)
- Supports transaction-date-specific historical rates
- Formula: `amount * from_rate / to_rate` (converts through CZK base)

**TransactionCategorizer** (`categorizer.py`):
- **Singleton pattern**: One instance shared across requests
- **Rule Matching**: Regex patterns on description, counterparty, amount
- **AI Integration**:
  - Token bucket rate limiting (10/min, 1000/day)
  - Exponential backoff on 429 errors
  - Historical context for better accuracy
  - Confidence scoring
- **Caching**: Loads rules from database once, refreshes on updates

**CNBExchangeRates** (`cnb_api.py`):
- Fetches daily rates from CNB XML API
- Falls back to nearby dates if specific date unavailable
- Disk cache in `data/cache/cnb_rates_{date}.json`
- Handles CNB-specific format (1 EUR = X CZK)

**Logger** (`logger.py`):
- Centralized logging configuration
- File output: `data/logs/finance_consolidator.log`
- Console output with color coding
- Rotation and size limits

## Data Flow Examples

### Example 1: File Upload

```
1. User drops ČSOB CSV file in UI
   ├─ Frontend: FileUpload.svelte
   └─ POST /api/v1/files/upload (multipart/form-data)

2. Backend creates job, starts background task
   ├─ Saves file to data/uploads/csob_20251231_123456.csv
   └─ Returns job_id

3. Background task processes file:
   ├─ FileParser loads config/institutions/csob.yaml
   ├─ Parses CSV rows (skip 2, delimiter=;)
   ├─ Maps columns to standard fields
   └─ Returns 150 raw transactions

4. DataNormalizer processes each transaction:
   ├─ Parse date: "31.10.2025" → datetime(2025, 10, 31)
   ├─ Parse amount: "-1 000,00" → Decimal(-1000.00)
   ├─ Convert: -1000.00 CZK → -1000.00 CZK (1:1)
   ├─ Generate ID: hash(date, amount, desc, ...) → TXN_20251031_a3f5b8c9
   └─ Returns Transaction object

5. Categorizer processes each transaction:
   ├─ Check internal transfer: No
   ├─ Match manual rules: "Tesco" → Spotreba > Jedlo > Supermarket
   └─ Returns: tier1, tier2, tier3, source=manual_rule

6. DatabaseWriter saves to SQLite:
   ├─ Find or create Institution(name="ČSOB")
   ├─ Find or create Account(number="283337817/0300")
   ├─ Check if transaction_id exists
   ├─ Mode=append → Skip if exists, Insert if new
   └─ Returns: {added: 150, updated: 0, skipped: 0}

7. Frontend polls job status every 2 seconds
   └─ Shows progress, logs, completion
```

### Example 2: Filtering Transactions

```
1. User sets filters:
   - Institution: Wise
   - From: 2025-01-01
   - Category Tier1: Spotreba Rodina
   - Search: "uber"

2. Frontend builds query params:
   {
     institution: "Wise",
     from_date: "2025-01-01",
     category_tier1: "Spotreba Rodina",
     search: "uber",
     skip: 0,
     limit: 50,
     sort_by: "date",
     sort_order: "desc"
   }

3. Backend (TransactionRepository.get_all):
   query = session.query(Transaction)
   ├─ .join(Institution).filter(name == "Wise")
   ├─ .filter(date >= "2025-01-01")
   ├─ .filter(category_tier1 == "Spotreba Rodina")
   ├─ .filter(description.ilike("%uber%"))
   ├─ .order_by(date.desc())
   ├─ .limit(50).offset(0)
   └─ Returns 23 transactions

4. Frontend renders table with 23 rows
```

### Example 3: Bulk Delete

```
1. User clicks "Select All Filtered (272)"
   ├─ Frontend: selectAllFiltered()
   ├─ Fetches ALL transactions with same filters (limit=100000)
   └─ Extracts IDs: [1, 2, 3, ..., 272]

2. User clicks "Delete Selected (272)"
   ├─ Shows confirmation dialog
   └─ User confirms

3. Frontend: deleteBatchTransactions()
   ├─ Loop through 272 IDs
   ├─ For each: DELETE /api/v1/transactions/{id}
   └─ Shows progress: "Deleted 150/272..."

4. Backend (each DELETE):
   ├─ TransactionRepository.delete(id)
   ├─ session.query(Transaction).filter(id=id).delete()
   └─ session.commit()

5. Frontend refreshes transaction list
```

## Security Considerations

### Data Protection
- **SQLite database** contains sensitive financial data → gitignored
- **Uploaded files** in `data/uploads/` → gitignored
- **No authentication** (designed for local/personal use)
- **No encryption** (rely on OS-level file permissions)

### API Security
- **CORS**: Configured for localhost:5173 only
- **Input Validation**: Pydantic schemas validate all inputs
- **SQL Injection**: SQLAlchemy ORM prevents injection
- **File Upload**: Validates file extensions and MIME types

### API Keys
- **Gemini API Key**: Stored in environment variable, never committed
- **CNB API**: Public, no key required
- **Rate Limiting**: Prevents API quota exhaustion

## Performance Optimization

### Database
- **Indexes**: Multi-column indexes on common query patterns
  - `(date)`, `(category_tier1, tier2, tier3)`, `(owner_id)`, etc.
- **Bulk Operations**: SQLAlchemy bulk_insert_mappings for large uploads
- **Connection Pooling**: SQLAlchemy session pooling

### Frontend
- **Lazy Loading**: Pagination with 50 items/page default
- **Debounced Search**: 300ms delay on search input
- **Client-Side Caching**: Category tree cached in component state
- **Virtual Scrolling**: Not implemented (future enhancement)

### File Processing
- **Streaming**: CSV files processed row-by-row (memory efficient)
- **Batch Writes**: Database writes in batches of 100
- **Background Tasks**: FastAPI BackgroundTasks for non-blocking uploads

## Testing Strategy

### Unit Tests
```
tests/
├── test_currency.py       # Currency conversion logic
├── test_date_parser.py    # Date parsing various formats
├── test_normalizer.py     # Transaction normalization
└── test_parser.py         # CSV/XLSX parsing
```

### Integration Tests
- End-to-end file upload and retrieval
- Rule application and categorization
- API endpoint validation

### Manual Testing
- Use `scripts/test_config.py` to test institution configs
- Use `scripts/test_upload.py` to simulate file uploads

## Deployment

### Development
```bash
# Terminal 1: Backend
uvicorn backend.app:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

### Production (Future)
- Backend: Uvicorn with Gunicorn workers
- Frontend: Static build served by nginx or CDN
- Database: Migrate to PostgreSQL for better concurrency
- Docker: Containerize for easy deployment

## Future Enhancements

### Planned Features
1. **Budget Tracking**: Monthly budgets per category
2. **Recurring Transactions**: Auto-detect subscriptions
3. **Multi-User**: User accounts with authentication
4. **Mobile App**: React Native or Flutter
5. **Bank API Integration**: Direct connection via PSD2/OpenBanking
6. **Investment Tracking**: Portfolio performance, dividends
7. **Receipts**: OCR for receipt scanning and matching

### Technical Debt
1. **Frontend Testing**: Add Vitest + Testing Library
2. **Type Safety**: Add TypeScript to frontend
3. **API Versioning**: Prepare for breaking changes
4. **Migration System**: Alembic for database schema changes
5. **Caching Layer**: Redis for API response caching
6. **Queue System**: Celery for long-running tasks

## Troubleshooting

### Common Issues

**Issue**: Currency conversion shows 1:1 for EUR
- **Cause**: Backend not loading settings.yaml properly
- **Fix**: Restart backend, ensure CNB API enabled

**Issue**: File upload stuck at "Processing..."
- **Cause**: Background task crashed
- **Fix**: Check logs at `data/logs/finance_consolidator.log`

**Issue**: Duplicate transactions on re-upload
- **Cause**: Transaction ID hash changed (config modified)
- **Fix**: Use "Override" mode or delete old transactions first

**Issue**: Frontend shows old data after changes
- **Cause**: Browser cache or pagination
- **Fix**: Hard refresh (Ctrl+Shift+R) or clear filters

## Contributing

When adding features:
1. Update this ARCHITECTURE.md with design decisions
2. Update CLAUDE.md with development guidance
3. Add tests for new functionality
4. Update API docs (FastAPI auto-generates from docstrings)

## References

- FastAPI: https://fastapi.tiangolo.com/
- Svelte: https://svelte.dev/
- SQLAlchemy: https://www.sqlalchemy.org/
- CNB Exchange Rates: https://www.cnb.cz/en/financial-markets/foreign-exchange-market/central-bank-exchange-rate-fixing/
- Google Gemini: https://ai.google.dev/
