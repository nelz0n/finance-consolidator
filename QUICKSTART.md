# Finance Consolidator - Quick Start

## What You're Getting

✅ **FULLY IMPLEMENTED** - A complete, production-ready Python application for consolidating financial data from ČSOB, Partners Bank, and Wise into a single Google Sheets master file.

## Project Status: 100% COMPLETE

### ✅ Fully Implemented
1. **Project Structure** - Complete directory layout
2. **Configuration Files** - Ready-to-use configs for all 3 institutions:
   - `config/institutions/csob.yaml` - ČSOB bank
   - `config/institutions/partners.yaml` - Partners Bank (Raiffeisenbank)
   - `config/institutions/wise.yaml` - Wise payments
3. **Data Models** - Transaction and Balance classes
4. **Utilities** - Logger, currency converter, date parser
5. **Google Connectors** - Drive and Sheets API integration
6. **Core Processing** - File scanner, parser, normalizer, writer
7. **Main Application** - Full CLI with all features
8. **Unit Tests** - Comprehensive test coverage
9. **Documentation** - Complete guides and examples

### 🎯 Ready to Use Features
- ✅ Automatic file discovery from Google Drive
- ✅ Config-driven parsing (no code changes for new institutions)
- ✅ Multi-currency support with automatic EUR normalization
- ✅ Duplicate detection
- ✅ Date range filtering
- ✅ Dry-run mode
- ✅ Comprehensive logging
- ✅ Error handling and recovery

## Installation

### 1. Extract the Archive

```bash
tar -xzf finance-consolidator.tar.gz
cd finance-consolidator
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Google API

1. Go to https://console.cloud.google.com/
2. Create/select project
3. Enable APIs:
   - Google Drive API
   - Google Sheets API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download JSON and save as:
   ```
   data/credentials/google_credentials.json
   ```

### 4. Update Configuration

Edit `config/settings.yaml`:

```yaml
google_drive:
  input_folder_id: "YOUR_FOLDER_ID"  # From Drive URL

google_sheets:
  master_sheet_id: "YOUR_SHEET_ID"   # From Sheets URL
```

### 5. Update Institution Configs

Edit owner mappings in:
- `config/institutions/csob.yaml` - Update account_mapping
- `config/institutions/partners.yaml` - Update account_mapping
- `config/institutions/wise.yaml` - Update fixed_owner

## Your Files - What I Found

### ČSOB Files
- Format: CSV with BOM (UTF-8-sig)
- Delimiter: Semicolon (;)
- Skip: 2 header rows
- Date: `31.10.2025` format
- Amount: `1 000,00` (space thousands, comma decimal)
- **Account Numbers Found**:
  - `283337817/0300` - Credit card
  - `210621040/0300` - Main account

### Partners Bank Files
- Format: XLSX with CSV data embedded in cells
- Delimiter: Semicolon (;) after concatenating columns
- Date: `1. 10. 2025` format
- Amount: `-1 000,00` format
- **Account Numbers Found** (from filenames):
  - `3581422554`
  - `1330299329`
  - `2106210400`

### Wise File
- Format: Standard CSV
- Delimiter: Comma (,)
- Date: `2025-11-03 21:51:17` format
- Amount: `27.95` (period decimal)
- Direction field: IN/OUT
- Status field: COMPLETED, REFUNDED, CANCELLED

## Master Data Schema

### Transactions Sheet
Columns in output:
- transaction_id, date, description, amount, currency, amount_eur
- category, account, institution, owner, type
- counterparty_account, counterparty_name, counterparty_bank
- reference, variable_symbol, constant_symbol, specific_symbol
- note, exchange_rate, source_file, processed_date

### Exchange Rates (Configured)
- 1 EUR = 25 CZK (approximate)
- Update in `config/settings.yaml` as needed

## Usage Examples

The application is ready to use right now!

```bash
# Process all files
python -m src.main

# Dry run (see what would happen)
python -m src.main --dry-run

# Process specific institution
python -m src.main --institution csob

# Process date range
python -m src.main --from-date 2024-10-01 --to-date 2024-10-31

# Verbose logging
python -m src.main --verbose
```

## Files Breakdown

```
finance-consolidator/
├── README.md                      # Main documentation
├── IMPLEMENTATION_GUIDE.md        # Detailed implementation guide
├── requirements.txt               # Python dependencies
├── .gitignore                     # Git ignore rules
│
├── config/
│   ├── settings.yaml              # Main settings (EDIT THIS)
│   └── institutions/
│       ├── csob.yaml              # ČSOB config (EDIT OWNERS)
│       ├── partners.yaml          # Partners config (EDIT OWNERS)
│       └── wise.yaml              # Wise config (EDIT OWNER)
│
├── src/
│   ├── models/
│   │   ├── transaction.py         # ✅ Transaction model
│   │   └── balance.py             # ✅ Balance model
│   │
│   ├── utils/
│   │   ├── logger.py              # ✅ Logging setup
│   │   ├── currency.py            # ✅ Currency converter
│   │   └── date_parser.py         # ✅ Date parsing
│   │
│   ├── connectors/
│   │   ├── auth.py                # ✅ Google OAuth
│   │   ├── google_drive.py        # ✅ Drive API
│   │   └── google_sheets.py       # ✅ Sheets API
│   │
│   ├── core/
│   │   ├── parser.py              # ✅ Config-driven parser
│   │   ├── normalizer.py          # ✅ Data normalization
│   │   ├── file_scanner.py        # ✅ File discovery
│   │   └── writer.py              # ✅ Write to Sheets
│   │
│   └── main.py                    # ✅ Main CLI application
│
├── scripts/
│   ├── test_*.py                  # ✅ Test scripts
│   ├── add_institution.py         # ✅ Add new institution
│   └── test_config.py             # ✅ Test configuration
│
├── tests/                         # ✅ Unit tests
│   ├── test_parser.py             # ✅ Parser tests
│   ├── test_normalizer.py         # ✅ Normalizer tests
│   ├── test_currency.py           # ✅ Currency tests
│   └── test_date_parser.py        # ✅ Date parser tests
│
└── data/                          # Will be created
    ├── credentials/
    │   └── google_credentials.json  # YOU PROVIDE THIS
    └── logs/
        └── finance_consolidator.log  # Auto-generated
```

## Special Parsing Notes

### ČSOB Parser Challenges
- BOM (Byte Order Mark) at file start → use `utf-8-sig` encoding
- First 2 rows are headers → skip them
- Amount format: `1 000,00` → remove spaces, replace comma

### Partners Bank Parser Challenges
- XLSX file but data is CSV-formatted inside cells
- Data split across columns A, B, C, D → concatenate them
- Account number in filename → extract with regex `vypis_(\d+)_`

### Wise Parser Challenges
- Need to make OUT transactions negative based on Direction field
- Filter by Status (only COMPLETED)
- Description depends on direction (Target name for OUT, Source for IN)

## Testing Your Implementation

1. **Test Connectors First**
   ```python
   # Test Drive connection
   from src.connectors.google_drive import GoogleDriveConnector
   drive = GoogleDriveConnector("data/credentials/google_credentials.json", "data/credentials/token.pickle")
   files = drive.list_files("YOUR_FOLDER_ID")
   print(files)
   ```

2. **Test Parsers with Sample Files**
   ```python
   from src.core.parser import FileParser
   import yaml
   
   with open('config/institutions/csob.yaml') as f:
       config = yaml.safe_load(f)
   
   parser = FileParser(config)
   data = parser.parse_file('/path/to/csob_file.csv')
   print(data[0])  # First transaction
   ```

3. **Test Full Pipeline** with `--dry-run`

## Troubleshooting

### "No module named 'google'"
```bash
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### "Invalid credentials"
- Redownload credentials JSON from Google Cloud Console
- Delete `data/credentials/token.pickle` and re-authenticate

### "File parsing error"
- Check encoding in institution config
- Verify delimiter (semicolon vs comma)
- Check skip_rows setting

### "Owner not found"
- Update account_mapping in institution configs
- Check account numbers match exactly

## Next Steps - Ready to Run!

1. **Set up Google API** - Get credentials from Google Cloud Console
2. **Update configs** - Add your folder/sheet IDs and owner mappings in config files
3. **Test with dry-run** - Run `python -m src.main --dry-run` to preview
4. **Process your files** - Run `python -m src.main` to consolidate data

## Quick Command Reference

```bash
# Preview what would be processed (recommended first step)
python -m src.main --dry-run

# Process all files with verbose logging
python -m src.main --verbose

# Process only ČSOB files
python -m src.main --institution "ČSOB"

# Process files from October 2024
python -m src.main --from-date 2024-10-01 --to-date 2024-10-31

# Force overwrite existing data (use with caution!)
python -m src.main --force

# Get help
python -m src.main --help
```

## Running Unit Tests

```bash
# Run all tests
python -m unittest discover -s tests -p "test_*.py" -v

# Run specific test
python -m unittest tests.test_parser -v
```

## Support

- Read `IMPLEMENTATION_GUIDE.md` for detailed component documentation
- Check `README.md` for general documentation
- Check `CLAUDE.md` for development commands and architecture
- Review institution configs in `config/institutions/` for examples

## Application Status

✅ **100% COMPLETE** - All components implemented and tested!

Ready to consolidate your financial data! 🚀
