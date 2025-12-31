# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Finance consolidation tool that aggregates banking and investment data from multiple Czech financial institutions (ČSOB, Partners Bank, Wise) into a SQLite database. The system provides a web UI for uploading CSV/XLSX files, automatically normalizing transactions, applying categorization rules, and browsing/managing financial data.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Start backend API server (from project root)
uvicorn backend.app:app --reload --port 8000

# In a separate terminal, start frontend dev server
cd frontend
npm run dev

# Access web UI at:
# http://localhost:5173
```

### Testing and Configuration Management
```bash
# Test institution configuration with a sample file
python scripts/test_config.py --institution "ČSOB" --file data/temp/csob_export.csv
python scripts/test_config.py -i Wise -f data/temp/transaction-history.csv --all

# Interactive wizard to add new institution
# - Guides you through all configuration options
# - Supports CSV and XLSX formats
# - Automatically generates YAML config file
python scripts/add_institution.py
```

## Architecture Overview

### Data Flow Pipeline
1. **File Upload** - Web UI accepts CSV/XLSX files via drag-and-drop or file picker
2. **Parser** - Fully config-driven parser handles CSV and XLSX formats based on institution configuration
   - New institutions work automatically without code changes
   - Supports transformations (concatenate, strip, replace, split)
   - Backward compatible with old config format
3. **Normalizer** - Converts raw data into standardized Transaction objects with currency normalization
4. **Categorizer** - Applies rule-based categorization (loaded from SQLite database)
5. **Database Writer** - Persists transactions to SQLite database

### Core Components

**Models** (`src/models/`)
- `Transaction` - Financial transaction with 20+ fields (date, amount, currency, counterparty, etc.)
- `Balance` - Account balance or investment position

**Utilities** (`src/utils/`)
- `CurrencyConverter` - Multi-currency conversion with configurable rates (CZK ↔ EUR)
- `CNBExchangeRates` - Real-time exchange rates from Czech National Bank API
- `TransactionCategorizer` - 3-tier categorization with AI fallback (loads rules from SQLite database)
  - Rate limiting (10 req/min, 1000/day) with token bucket algorithm
  - Exponential backoff retry logic for 429 errors (2s, 4s, 8s delays)
  - Daily quota tracking to prevent exceeding API limits
- `date_parser` - Handles multiple date formats across institutions
- `logger` - Centralized logging configuration

**Backend API** (`backend/api/`)
- `transactions.py` - CRUD operations for transactions, filtering, bulk updates, re-apply rules
- `categories.py` - Category tree management (3-tier hierarchy)
- `rules.py` - Categorization rules CRUD and rule testing
- `dashboard.py` - Summary statistics and analytics
- `files.py` - File upload and processing endpoint with background tasks
- `settings.py` - Configuration management
- `accounts.py` - Account descriptions management

**Core Processing** (`src/core/`)
- `FileParser` - Config-driven CSV/XLSX parser with transformation support
  - Automatically routes to correct parser based on `format.type` configuration
  - Applies transformations (concatenate, strip, replace, split) before mapping
  - Special handling for Partners Bank (concatenated columns A-D)
  - `extract_from_filename` - Extracts account from filename (e.g., vypis_1330299329_*.xlsx → 1330299329)
  - `account_bank_code` - Auto-appends bank code suffix (e.g., /6363 for Partners Bank → 1330299329/6363)
- `DataNormalizer` - Converts raw data to Transaction objects
  - Treats "/" as empty value in field cleaning (prevents "/" in empty counterparty_account)
- `DatabaseWriter` - Persists normalized transactions to SQLite database

### Configuration System

**Main Settings** (`config/settings.yaml`)
- Currency rates and base currency
- Processing options (batch size, date format, timezone)
- Logging configuration
- Data quality validation rules
- Institution configuration paths

**Institution Configs** (`config/institutions/*.yaml`)
Each institution has a YAML config with:
- `file_detection` - Filename patterns for auto-detection
- `csv_format` - Encoding, delimiter, header info, rows to skip
- `column_mapping` - Maps CSV columns to standardized fields
- `transformations` - Date format, amount parsing (decimal/thousands separators)
- `owner_detection` - Maps account numbers to owners
- `category_mapping` - Translates institution categories to standard ones

### Institution-Specific Parsing Quirks

**ČSOB**
- UTF-8-sig encoding (BOM)
- Skip first 2 rows (account summary, empty line)
- Semicolon delimiter
- Date format: `dd.mm.YYYY`
- Amount format: `1 000,00` (space thousands, comma decimal)
- Rich transaction metadata (variable/constant/specific symbols)

**Partners Bank**
- XLSX format (not CSV)
- Data split across columns A-D, must concatenate then split by semicolon
- Extract account number from filename: `vypis_(\d+)_` (e.g., vypis_1330299329_*.xlsx)
- **NEW**: Auto-appends bank code /6363 via `account_bank_code` config (1330299329 → 1330299329/6363)
- Date format: `d. m. Y` (with spaces)
- Amount format: `-1 000,00`

**Wise**
- Standard CSV with comma delimiter
- Filter: Only `Status == "COMPLETED"`
- Amount sign from Direction field: `OUT`=negative, `IN`=positive
- Description varies: `OUT`→Target name, `IN`→Source name
- ISO datetime format: `%Y-%m-%d %H:%M:%S`

## Key Data Structures

### Transaction Object
20+ fields including core data (date, amount, currency), counterparty info (account, name, bank), Czech banking symbols (variable/constant/specific), metadata (source file, processed date), and normalized EUR amount.

### Currency Handling
- Base currency: CZK (configurable in settings.yaml)
- Conversion: `amount / from_rate * to_rate` (converts through base currency)
- Static rates defined in config (EUR: 1.0, CZK: 25.0)
- All transactions normalized to EUR in `amount_eur` field

### Owner Detection
Account numbers mapped to owners in institution configs. Example:
```yaml
owner_detection:
  method: "account_mapping"
  account_mapping:
    "283337817/0300": "Branislav"
    "210621040/0300": "Branislav"
  default_owner: "Unknown"
```

## Adding New Institutions

When adding support for a new financial institution:

1. Create `config/institutions/new_bank.yaml` following the structure of existing configs
2. Define `file_detection.filename_patterns` for auto-discovery
3. Specify `csv_format` (encoding, delimiter, skip_rows)
4. Map columns in `column_mapping` section
5. Configure `transformations` for date and amount parsing
6. Set up `owner_detection` and `category_mapping`
7. Test with `python scripts/test_config.py --institution new_bank --file sample.csv`

The system auto-discovers institution configs if `institutions.auto_discover: true` in settings.yaml.

## Security Notes

**Never commit:**
- `data/` directory contents (contains sensitive financial data)
- `.env` files
- `data/finance.db` (SQLite database with transaction data)

The `.gitignore` should already exclude these paths.

## Error Handling Strategy

- **Parser errors** - Log warning, skip row, continue processing
- **Normalization errors** - Log warning, use defaults or None for missing fields
- **Database errors** - Log error, rollback transaction, return error to UI
- **File upload errors** - Return HTTP 400/500 with error details
- **Critical errors** - Log critical, return error response to frontend

All errors logged to `data/logs/finance_consolidator.log`.
