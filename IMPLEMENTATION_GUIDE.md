# Implementation Guide - Remaining Components

This document describes the remaining components that need to be implemented. I've created the foundation, and this guide will help you complete the implementation.

## Already Completed ✅

1. **Project Structure** - All directories created
2. **Configuration Files**
   - ČSOB configuration (csob.yaml)
   - Partners Bank configuration (partners.yaml)
   - Wise configuration (wise.yaml)
   - Settings template (settings.yaml)
3. **Data Models**
   - Transaction model
   - Balance model
4. **Utilities**
   - Logger
   - Currency converter
   - Date parser
5. **Documentation**
   - README.md
   - This implementation guide

## Components to Implement

### 1. Google Connectors

#### `src/connectors/google_drive.py`

**Purpose**: Connect to Google Drive, list files, download files

**Key Functions**:
```python
class GoogleDriveConnector:
    def __init__(self, credentials_path, token_path):
        # Initialize Drive API client
        
    def authenticate(self):
        # Handle OAuth flow
        
    def list_files(self, folder_id, file_pattern=None):
        # List files matching pattern in folder
        # Returns: List of {id, name, modified_time}
        
    def download_file(self, file_id, destination):
        # Download file to local path
        
    def get_file_content(self, file_id):
        # Get file content directly (for CSV)
```

**Key Libraries**:
- `google.oauth2.credentials`
- `googleapiclient.discovery`
- `google_auth_oauthlib.flow`

**OAuth Flow**:
1. Check if token exists
2. If not, run OAuth flow with credentials
3. Save token for future use

#### `src/connectors/google_sheets.py`

**Purpose**: Read from and write to Google Sheets

**Key Functions**:
```python
class GoogleSheetsConnector:
    def __init__(self, credentials_path, token_path):
        # Initialize Sheets API client
        
    def read_sheet(self, spreadsheet_id, range_name):
        # Read data from sheet
        # Returns: List of lists (rows)
        
    def write_sheet(self, spreadsheet_id, range_name, values):
        # Write data to sheet
        # values: List of lists (rows)
        
    def append_sheet(self, spreadsheet_id, range_name, values):
        # Append data to end of sheet
        
    def create_tab(self, spreadsheet_id, tab_name):
        # Create new tab if doesn't exist
        
    def clear_sheet(self, spreadsheet_id, range_name):
        # Clear data from range
```

### 2. Core Processing

#### `src/core/parser.py`

**Purpose**: Parse CSV/XLSX files based on institution config

**Key Class**:
```python
class FileParser:
    def __init__(self, institution_config):
        self.config = institution_config
        
    def parse_file(self, file_path):
        # Main parsing logic
        # Returns: List of raw transaction dicts
        
    def _parse_csob_csv(self, file_path):
        # ČSOB specific: skip 2 rows, handle BOM, semicolon delimiter
        
    def _parse_partners_xlsx(self, file_path):
        # Partners specific: XLSX with CSV data in cells
        # Need to concatenate columns A, B, C, D
        # Then split by semicolon
        
    def _parse_wise_csv(self, file_path):
        # Wise specific: standard CSV
        
    def _extract_account_from_filename(self, filename):
        # For Partners: extract account from vypis_<account>_<dates>.xlsx
```

**Special Handling**:

**ČSOB**:
- Skip first 2 lines
- UTF-8-sig encoding (BOM)
- Semicolon delimiter
- Comma decimal separator, space thousands

**Partners Bank**:
- XLSX file
- Read cells A, B, C, D
- Concatenate to get full CSV row
- Split by semicolon
- Extract account from filename: `vypis_(\d+)_`

**Wise**:
- Standard CSV
- Handle Direction field (IN/OUT)
- Make OUT negative, IN positive
- Use Status to filter

#### `src/core/normalizer.py`

**Purpose**: Convert raw parsed data to Transaction/Balance objects

**Key Class**:
```python
class DataNormalizer:
    def __init__(self, currency_converter, institution_config):
        self.converter = currency_converter
        self.config = institution_config
        
    def normalize_transaction(self, raw_data, filename):
        # Convert raw dict to Transaction object
        # Apply transformations from config
        # Return Transaction object
        
    def _parse_amount(self, amount_str, decimal_sep, thousands_sep):
        # Handle: "1 000,00" or "1,000.00" or "-1000"
        # Return Decimal
        
    def _apply_category_mapping(self, source_category):
        # Map institution category to standard category
        
    def _determine_owner(self, raw_data, account):
        # Use owner_detection config
        
    def _generate_transaction_id(self, date, sequence):
        # Generate unique ID: TXN_20241015_001
```

#### `src/core/file_scanner.py`

**Purpose**: Scan Google Drive for files to process

**Key Functions**:
```python
class FileScanner:
    def __init__(self, drive_connector, institutions_config):
        self.drive = drive_connector
        self.institutions = institutions_config
        
    def scan_for_files(self, folder_id):
        # Scan folder for files matching institution patterns
        # Returns: List of {file_id, filename, institution, modified_time}
        
    def match_institution(self, filename):
        # Match filename to institution config
        # Returns: institution_name or None
```

#### `src/core/writer.py`

**Purpose**: Write transactions to Google Sheets

**Key Class**:
```python
class SheetsWriter:
    def __init__(self, sheets_connector, sheet_id):
        self.sheets = sheets_connector
        self.sheet_id = sheet_id
        
    def write_transactions(self, transactions, tab_name="Transactions"):
        # Write list of Transaction objects to sheet
        # Convert to rows first
        
    def write_balances(self, balances, tab_name="Balances"):
        # Write list of Balance objects to sheet
```

### 3. Main Orchestration

#### `src/main.py`

**Purpose**: Main entry point, orchestrate the entire process

**Structure**:
```python
import argparse
import yaml
from pathlib import Path

def load_config(config_path="config/settings.yaml"):
    # Load main settings
    
def load_institution_configs(config_dir="config/institutions"):
    # Load all institution YAML files
    # Returns: Dict of {institution_name: config}
    
def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--institution', type=str)
    parser.add_argument('--from-date', type=str)
    parser.add_argument('--to-date', type=str)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()
    
    # 1. Load configurations
    settings = load_config()
    institutions = load_institution_configs()
    
    # 2. Setup logger
    from src.utils import setup_logger
    logger = setup_logger(
        level='DEBUG' if args.verbose else settings['logging']['level'],
        log_file=settings['logging']['file']
    )
    
    # 3. Initialize connectors
    from src.connectors.google_drive import GoogleDriveConnector
    from src.connectors.google_sheets import GoogleSheetsConnector
    
    drive = GoogleDriveConnector(
        settings['google_drive']['credentials_path'],
        settings['google_drive']['token_path']
    )
    
    sheets = GoogleSheetsConnector(
        settings['google_drive']['credentials_path'],
        settings['google_drive']['token_path']
    )
    
    # 4. Initialize currency converter
    from src.utils import CurrencyConverter
    converter = CurrencyConverter(
        rates=settings['currency']['rates'],
        base_currency=settings['currency']['base_currency']
    )
    
    # 5. Scan for files
    from src.core.file_scanner import FileScanner
    scanner = FileScanner(drive, institutions)
    files = scanner.scan_for_files(settings['google_drive']['input_folder_id'])
    
    # Filter by institution if specified
    if args.institution:
        files = [f for f in files if f['institution'] == args.institution]
    
    logger.info(f"Found {len(files)} files to process")
    
    # 6. Process each file
    from src.core.parser import FileParser
    from src.core.normalizer import DataNormalizer
    
    all_transactions = []
    
    for file_info in files:
        logger.info(f"Processing: {file_info['filename']}")
        
        # Download file
        local_path = f"/tmp/{file_info['filename']}"
        drive.download_file(file_info['file_id'], local_path)
        
        # Parse file
        inst_config = institutions[file_info['institution']]
        parser = FileParser(inst_config)
        raw_data = parser.parse_file(local_path)
        
        # Normalize data
        normalizer = DataNormalizer(converter, inst_config)
        for raw_txn in raw_data:
            txn = normalizer.normalize_transaction(raw_txn, file_info['filename'])
            if txn:
                all_transactions.append(txn)
    
    logger.info(f"Processed {len(all_transactions)} transactions")
    
    # 7. Filter by date range if specified
    if args.from_date or args.to_date:
        from src.utils import get_date_range
        start, end = get_date_range(args.from_date, args.to_date)
        
        if start:
            all_transactions = [t for t in all_transactions if t.date >= start]
        if end:
            all_transactions = [t for t in all_transactions if t.date <= end]
        
        logger.info(f"After date filtering: {len(all_transactions)} transactions")
    
    # 8. Write to Google Sheets (if not dry run)
    if args.dry_run:
        logger.info("Dry run - not writing to sheets")
        # Print summary
        for txn in all_transactions[:10]:
            print(f"{txn.date} | {txn.amount} {txn.currency} | {txn.description}")
    else:
        from src.core.writer import SheetsWriter
        writer = SheetsWriter(sheets, settings['google_sheets']['master_sheet_id'])
        writer.write_transactions(
            all_transactions,
            settings['google_sheets']['transactions_tab']
        )
        logger.info("Successfully written to Google Sheets")

if __name__ == "__main__":
    main()
```

### 4. Helper Scripts

#### `scripts/setup_credentials.py`

**Purpose**: Help user set up Google API credentials

```python
# Guide user through:
# 1. Go to Google Cloud Console
# 2. Enable APIs
# 3. Create credentials
# 4. Download and save to data/credentials/
```

#### `scripts/add_institution.py`

**Purpose**: Interactive wizard to add new institution

```python
# Ask user questions:
# - Institution name
# - File patterns
# - CSV format (delimiter, encoding)
# - Column names
# - Date format
# - Owner detection method
# Generate YAML config file
```

#### `scripts/test_config.py`

**Purpose**: Test institution configuration with sample file

```python
# Load config
# Parse sample file
# Show parsed data
# Validate configuration
```

## Implementation Order

1. **Week 1: Connectors**
   - Implement `google_drive.py`
   - Implement `google_sheets.py`
   - Test authentication and basic read/write

2. **Week 2: Parsing**
   - Implement `parser.py` with all three institution parsers
   - Implement `normalizer.py`
   - Test with sample files

3. **Week 3: Integration**
   - Implement `file_scanner.py`
   - Implement `writer.py`
   - Implement `main.py`
   - End-to-end testing

4. **Week 4: Polish**
   - Implement helper scripts
   - Add error handling
   - Write tests
   - Documentation

## Testing Strategy

### Unit Tests
- Test each parser with sample files
- Test normalizer with various inputs
- Test currency converter
- Test date parser

### Integration Tests
- Test file scanning
- Test full pipeline with sample data
- Test Google API connections

### Manual Testing
- Process your actual files
- Verify data in Google Sheets
- Check edge cases

## Common Issues and Solutions

### Issue: Partners Bank XLSX parsing

**Problem**: Data split across columns

**Solution**:
```python
import openpyxl

wb = openpyxl.load_workbook(file_path)
ws = wb.active

for row in range(2, ws.max_row + 1):
    # Concatenate columns A, B, C, D
    parts = []
    for col in ['A', 'B', 'C', 'D']:
        cell_value = ws[f'{col}{row}'].value
        if cell_value:
            parts.append(str(cell_value))
    
    full_row = ''.join(parts)
    fields = full_row.split(';')
    # Now parse fields...
```

### Issue: Amount parsing

**Problem**: Different formats (1 000,00 vs 1,000.00)

**Solution**:
```python
def parse_amount(amount_str, decimal_sep=',', thousands_sep=' '):
    # Remove currency symbols
    amount_str = amount_str.replace('CZK', '').replace('EUR', '').strip()
    
    # Remove thousands separator
    amount_str = amount_str.replace(thousands_sep, '')
    
    # Replace decimal separator with period
    amount_str = amount_str.replace(decimal_sep, '.')
    
    # Convert to Decimal
    return Decimal(amount_str)
```

### Issue: Date parsing

**Problem**: "1. 10. 2025" vs "31.10.2025"

**Solution**: Use the `parse_czech_date()` function from `date_parser.py`

## Next Steps

1. **Update settings.yaml**
   - Add your Google Drive folder ID
   - Add your Google Sheets ID
   - Update exchange rates if needed

2. **Get Google API credentials**
   - Follow README instructions
   - Save to `data/credentials/google_credentials.json`

3. **Start implementing**
   - Begin with `google_drive.py` and `google_sheets.py`
   - Test with sample files
   - Build incrementally

4. **Test with your data**
   - Start with one institution
   - Verify in Google Sheets
   - Then expand to all institutions

## Questions?

If you get stuck on any component, refer to:
- Python Google API documentation
- Sample files in `/mnt/user-data/uploads`
- Institution configs in `config/institutions/`
- This implementation guide

Good luck with the implementation!
