# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Finance consolidation tool that aggregates banking and investment data from multiple Czech financial institutions (ČSOB, Partners Bank, Wise) into a unified Google Sheets master file. The system processes CSV/XLSX files from Google Drive, normalizes transactions across different formats, and writes consolidated data to Google Sheets.

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
# Process all new files
python -m src.main

# Dry run mode (see what would be processed without writing)
python -m src.main --dry-run

# Process specific institution
python -m src.main --institution csob

# Process date range
python -m src.main --from-date 2024-10-01 --to-date 2024-10-31

# Verbose logging
python -m src.main --verbose

# Force reprocess (overwrite existing data)
python -m src.main --force
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
1. **File Scanner** - Lists files in Google Drive folder, matches filenames to institution patterns
2. **Parser** - Fully config-driven parser handles CSV and XLSX formats based on institution configuration
   - New institutions work automatically without code changes
   - Supports transformations (concatenate, strip, replace, split)
   - Backward compatible with old config format
3. **Normalizer** - Converts raw data into standardized Transaction/Balance objects with currency normalization
4. **Writer** - Formats and writes normalized data to Google Sheets

### Core Components

**Models** (`src/models/`)
- `Transaction` - Financial transaction with 20+ fields (date, amount, currency, counterparty, etc.)
- `Balance` - Account balance or investment position

**Utilities** (`src/utils/`)
- `CurrencyConverter` - Multi-currency conversion with configurable rates (CZK ↔ EUR)
- `date_parser` - Handles multiple date formats across institutions
- `logger` - Centralized logging configuration

**Connectors** (`src/connectors/`)
- Google Drive API connector (list files, download)
- Google Sheets API connector (read, write, append)

**Core Processing** (`src/core/`)
- `FileParser` - Config-driven CSV/XLSX parser with transformation support
  - Automatically routes to correct parser based on `format.type` configuration
  - Applies transformations (concatenate, strip, replace, split) before mapping
  - Special handling for Partners Bank (concatenated columns A-D)
- `DataNormalizer` - Converts raw data to Transaction objects
- `SheetsWriter` - Writes data to Google Sheets with append/overwrite modes

### Configuration System

**Main Settings** (`config/settings.yaml`)
- Google Drive/Sheets IDs and credentials paths
- Currency rates and base currency
- Processing options (batch size, date format, timezone)
- Logging configuration
- Data quality validation rules

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
- Extract account number from filename: `vypis_(\d+)_`
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

## Google API Setup Requirements

1. Enable Google Drive API and Google Sheets API in Google Cloud Console
2. Create OAuth 2.0 Client ID credentials for Desktop app
3. Download credentials JSON to `data/credentials/google_credentials.json`
4. First run will prompt for authentication and create `token.pickle`
5. Configure Drive folder ID and Sheet ID in `config/settings.yaml`

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
- `data/credentials/google_credentials.json` (Google OAuth credentials)
- `data/credentials/token.pickle` (Authentication token)
- `data/` directory contents (contains sensitive financial data)
- `.env` files

The `.gitignore` should already exclude these paths.

## Error Handling Strategy

- **Parser errors** - Log warning, skip row, continue processing
- **Normalization errors** - Log warning, use defaults or None for missing fields
- **Google API errors** - Log error, retry with exponential backoff
- **Critical errors** - Log critical, exit gracefully

All errors logged to `data/logs/finance_consolidator.log`.
