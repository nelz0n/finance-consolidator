# Finance Consolidator - Quick Start

## What You're Getting

A complete Python project structure for consolidating financial data from ČSOB, Partners Bank, and Wise into a single Google Sheets master file.

## Project Contents

### ✅ Fully Implemented
1. **Project Structure** - Complete directory layout
2. **Configuration Files** - Ready-to-use configs for all 3 institutions:
   - `config/institutions/csob.yaml` - ČSOB bank
   - `config/institutions/partners.yaml` - Partners Bank (Raiffeisenbank)
   - `config/institutions/wise.yaml` - Wise payments
3. **Data Models** - Transaction and Balance classes
4. **Utilities** - Logger, currency converter, date parser
5. **Documentation** - README, implementation guides

### 🔨 To Be Implemented (Phase 2)
- Google Drive connector
- Google Sheets connector
- File parsers (ČSOB, Partners, Wise)
- Data normalizer
- Main orchestration script

Full implementation guide provided in `IMPLEMENTATION_GUIDE.md`

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

## Implementation Phases

### Phase 1: Core Infrastructure (Do This First)
Implement:
1. `src/connectors/google_drive.py` - Drive API
2. `src/connectors/google_sheets.py` - Sheets API
3. Test authentication

**Estimated Time**: 2-3 days

### Phase 2: Parsing Logic
Implement:
1. `src/core/parser.py` - All three parsers
2. `src/core/normalizer.py` - Data normalization
3. Test with sample files

**Estimated Time**: 3-4 days

### Phase 3: Integration
Implement:
1. `src/core/file_scanner.py` - File discovery
2. `src/core/writer.py` - Write to Sheets
3. `src/main.py` - Orchestration
4. End-to-end testing

**Estimated Time**: 2-3 days

### Phase 4: Polish
Implement:
1. Helper scripts
2. Error handling
3. Tests
4. Final documentation

**Estimated Time**: 2-3 days

## Usage Examples

Once implemented:

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
│   │   ├── google_drive.py        # 🔨 TO IMPLEMENT
│   │   └── google_sheets.py       # 🔨 TO IMPLEMENT
│   │
│   ├── core/
│   │   ├── parser.py              # 🔨 TO IMPLEMENT
│   │   ├── normalizer.py          # 🔨 TO IMPLEMENT
│   │   ├── file_scanner.py        # 🔨 TO IMPLEMENT
│   │   └── writer.py              # 🔨 TO IMPLEMENT
│   │
│   └── main.py                    # 🔨 TO IMPLEMENT
│
├── scripts/
│   ├── setup_credentials.py       # 🔨 Helper for credentials
│   ├── add_institution.py         # 🔨 Add new institution
│   └── test_config.py             # 🔨 Test configuration
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

## Next Steps

1. **Set up Google API** - Get credentials
2. **Update configs** - Add your folder/sheet IDs and owner mappings
3. **Start implementing** - Follow IMPLEMENTATION_GUIDE.md
4. **Test incrementally** - Don't try to do everything at once
5. **Process your files** - Start with one institution, expand gradually

## Support

- Read `IMPLEMENTATION_GUIDE.md` for detailed component specs
- Check `README.md` for general documentation
- Review institution configs in `config/institutions/` for examples

## Estimated Timeline

- **Setup & Config**: 1 day
- **Phase 1 (Connectors)**: 2-3 days
- **Phase 2 (Parsers)**: 3-4 days
- **Phase 3 (Integration)**: 2-3 days
- **Phase 4 (Polish)**: 2-3 days

**Total**: 2-3 weeks of focused work

Good luck with the implementation! 🚀
