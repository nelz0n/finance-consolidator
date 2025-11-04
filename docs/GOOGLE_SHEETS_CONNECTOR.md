# Google Sheets Connector Documentation

## Overview

The `GoogleSheetsConnector` class provides a Python interface to the Google Sheets API for reading, writing, and managing spreadsheet data.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get Google API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Use the same project from Google Drive setup (or create new)
3. Enable the Google Sheets API
4. Use the same OAuth 2.0 credentials (or create new Desktop credentials)
5. Save as `data/credentials/google_credentials.json`

**Note**: You can use the same credentials file for both Drive and Sheets connectors.

### 3. Authentication

The connector uses the same OAuth flow as the Drive connector. If you've already authenticated for Drive, the token will be reused (but with Sheets permissions added).

## Usage

### Basic Example

```python
from src.connectors.google_sheets import GoogleSheetsConnector

# Initialize connector
sheets = GoogleSheetsConnector(
    credentials_path="data/credentials/google_credentials.json",
    token_path="data/credentials/token.pickle"
)

# Authenticate
if not sheets.authenticate():
    print("Authentication failed!")
    exit(1)

# Read data from sheet
spreadsheet_id = "your-spreadsheet-id"
data = sheets.read_sheet(spreadsheet_id, "Sheet1!A1:D10")

for row in data:
    print(row)
```

### Finding Spreadsheet ID

Open your Google Sheet in browser:
```
https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID/edit
```
The ID is the long string between `/d/` and `/edit`.

## Reading Data

### Read Specific Range

```python
# Read specific range
data = sheets.read_sheet(spreadsheet_id, "Sheet1!A1:D10")
# Returns: [['Header1', 'Header2', ...], ['Value1', 'Value2', ...], ...]

# Read entire sheet (specify sheet name only)
data = sheets.read_sheet(spreadsheet_id, "Transactions")

# Read specific columns
data = sheets.read_sheet(spreadsheet_id, "Sheet1!A:C")
```

### Get Sheet Names

```python
# Get list of all tabs/sheets in spreadsheet
sheet_names = sheets.get_sheet_names(spreadsheet_id)

for name in sheet_names:
    print(f"Sheet: {name}")
```

## Writing Data

### Overwrite Data

```python
# Prepare data (list of lists)
data = [
    ['Header1', 'Header2', 'Header3'],
    ['Value1', 'Value2', 'Value3'],
    ['Value4', 'Value5', 'Value6']
]

# Write to sheet (overwrites existing data)
sheets.write_sheet(spreadsheet_id, "Sheet1!A1", data)
```

### Append Data

```python
# Append rows to the end of existing data
new_rows = [
    ['New1', 'New2', 'New3'],
    ['New4', 'New5', 'New6']
]

# Appends after last row with data
sheets.append_sheet(spreadsheet_id, "Sheet1!A1", new_rows)
```

### Value Input Options

```python
# RAW: Values stored as-is (default)
sheets.write_sheet(spreadsheet_id, "Sheet1!A1", data, value_input_option="RAW")

# USER_ENTERED: Values parsed as if typed by user (formulas, dates, etc.)
sheets.write_sheet(spreadsheet_id, "Sheet1!A1", data, value_input_option="USER_ENTERED")
```

## Managing Sheets

### Create New Tab

```python
# Create new tab (no-op if already exists)
sheets.create_tab(spreadsheet_id, "Transactions")
sheets.create_tab(spreadsheet_id, "Balances")
```

### Clear Data

```python
# Clear specific range
sheets.clear_sheet(spreadsheet_id, "Sheet1!A1:Z100")

# Clear entire sheet
sheets.clear_sheet(spreadsheet_id, "Transactions")
```

## Advanced Operations

### Batch Update

Update multiple ranges in a single API call (more efficient):

```python
batch_data = [
    {
        'range': 'Transactions!A1:C1',
        'values': [['transaction_id', 'date', 'amount']]
    },
    {
        'range': 'Balances!A1:C1',
        'values': [['balance_id', 'date', 'value']]
    },
    {
        'range': 'Summary!A1',
        'values': [['Last Updated'], [datetime.now().strftime('%Y-%m-%d')]]
    }
]

sheets.batch_update(spreadsheet_id, batch_data)
```

### Format Cells

```python
# Apply formatting to a range
format_options = {
    'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
    'textFormat': {
        'bold': True,
        'fontSize': 12
    }
}

# Format header row (row 0, columns 0-9)
sheets.format_cells(
    spreadsheet_id=spreadsheet_id,
    sheet_id=0,  # Sheet ID (not name)
    start_row=0,
    end_row=1,
    start_col=0,
    end_col=10,
    format_options=format_options
)
```

## API Reference

### `GoogleSheetsConnector(credentials_path, token_path)`

Initialize the Google Sheets connector.

**Parameters:**
- `credentials_path` (str): Path to Google API credentials JSON
- `token_path` (str): Path to store/load authentication token

### `authenticate() -> bool`

Authenticate with Google Sheets API.

**Returns:**
- `bool`: True if successful, False otherwise

### `read_sheet(spreadsheet_id, range_name) -> Optional[List[List[Any]]]`

Read data from a sheet.

**Parameters:**
- `spreadsheet_id` (str): The spreadsheet ID
- `range_name` (str): A1 notation (e.g., "Sheet1!A1:D10")

**Returns:**
- `List[List[Any]]`: List of rows, or None if error

### `write_sheet(spreadsheet_id, range_name, values, value_input_option="RAW") -> bool`

Write data to a sheet (overwrites).

**Parameters:**
- `spreadsheet_id` (str): The spreadsheet ID
- `range_name` (str): A1 notation starting cell
- `values` (List[List[Any]]): Data to write
- `value_input_option` (str): "RAW" or "USER_ENTERED"

**Returns:**
- `bool`: True if successful, False otherwise

### `append_sheet(spreadsheet_id, range_name, values, value_input_option="RAW") -> bool`

Append data to end of sheet.

**Parameters:**
- Same as `write_sheet`

**Returns:**
- `bool`: True if successful, False otherwise

### `create_tab(spreadsheet_id, tab_name) -> bool`

Create a new tab/sheet.

**Parameters:**
- `spreadsheet_id` (str): The spreadsheet ID
- `tab_name` (str): Name for the new tab

**Returns:**
- `bool`: True if created or already exists, False if error

### `clear_sheet(spreadsheet_id, range_name) -> bool`

Clear data from a range.

**Parameters:**
- `spreadsheet_id` (str): The spreadsheet ID
- `range_name` (str): A1 notation range to clear

**Returns:**
- `bool`: True if successful, False otherwise

### `get_sheet_names(spreadsheet_id) -> Optional[List[str]]`

Get all tab names in spreadsheet.

**Parameters:**
- `spreadsheet_id` (str): The spreadsheet ID

**Returns:**
- `List[str]`: List of sheet names, or None if error

### `batch_update(spreadsheet_id, data) -> bool`

Update multiple ranges in one request.

**Parameters:**
- `spreadsheet_id` (str): The spreadsheet ID
- `data` (List[Dict]): List of dicts with 'range' and 'values' keys

**Returns:**
- `bool`: True if successful, False otherwise

### `format_cells(spreadsheet_id, sheet_id, start_row, end_row, start_col, end_col, format_options) -> bool`

Apply formatting to cells.

**Parameters:**
- `spreadsheet_id` (str): The spreadsheet ID
- `sheet_id` (int): Sheet ID (not name)
- `start_row` (int): Starting row (0-based)
- `end_row` (int): Ending row (exclusive)
- `start_col` (int): Starting column (0-based)
- `end_col` (int): Ending column (exclusive)
- `format_options` (Dict): Formatting options

**Returns:**
- `bool`: True if successful, False otherwise

## Complete Example: Writing Transactions

```python
from datetime import datetime
from src.connectors import GoogleSheetsConnector
from src.utils import setup_logger

# Setup
logger = setup_logger(level='INFO', console=True)
sheets = GoogleSheetsConnector(
    "data/credentials/google_credentials.json",
    "data/credentials/token.pickle"
)

# Authenticate
if not sheets.authenticate():
    logger.error("Failed to authenticate")
    exit(1)

# Spreadsheet ID
spreadsheet_id = "10H6uDqvYs2iBpwBDxH-zEfSrSMAq6J5JbjKVR5NkG_w"

# Create Transactions tab if needed
sheets.create_tab(spreadsheet_id, "Transactions")

# Clear existing data
sheets.clear_sheet(spreadsheet_id, "Transactions!A:Z")

# Prepare headers
headers = [
    'transaction_id', 'date', 'description', 'amount',
    'currency', 'amount_eur', 'category', 'institution', 'owner'
]

# Prepare transaction data
transactions = [
    ['TXN_20241101_001', '2024-11-01', 'ČSOB Payment', -1100.00,
     'CZK', -44.00, 'Dining', 'ČSOB', 'Branislav'],
    ['TXN_20241101_002', '2024-11-01', 'Wise Transfer', 500.00,
     'EUR', 500.00, 'Income', 'Wise', 'Branislav'],
    ['TXN_20241102_001', '2024-11-02', 'Partners Investment', 10000.00,
     'CZK', 400.00, 'Investment', 'Partners', 'Branislav']
]

# Combine headers and data
all_data = [headers] + transactions

# Write to sheet
if sheets.write_sheet(spreadsheet_id, "Transactions!A1", all_data):
    logger.info(f"✓ Wrote {len(transactions)} transactions")
    logger.info(f"View at: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
else:
    logger.error("Failed to write data")
```

## Testing

Run the test script:

```bash
python scripts/test_sheets_connection.py
```

This will:
1. Authenticate with Google Sheets
2. List existing sheets
3. Create test tabs
4. Write test data
5. Read it back
6. Test append functionality
7. Clear test data
8. Test batch updates

## A1 Notation Guide

### Range Formats

```python
# Single cell
"Sheet1!A1"

# Range of cells
"Sheet1!A1:D10"

# Entire column
"Sheet1!A:A"

# Multiple columns
"Sheet1!A:D"

# Entire row
"Sheet1!1:1"

# Multiple rows
"Sheet1!1:10"

# Entire sheet
"Sheet1"

# Starting from cell
"Sheet1!A1"  # For append, starts here and goes to end
```

### Column Letters

```
A = 0, B = 1, C = 2, ..., Z = 25, AA = 26, AB = 27, ...
```

## Error Handling

```python
from src.connectors import GoogleSheetsConnector
from src.utils import setup_logger

logger = setup_logger(level='INFO', console=True)
sheets = GoogleSheetsConnector(creds_path, token_path)

# Check authentication
if not sheets.authenticate():
    logger.error("Authentication failed - check credentials")
    exit(1)

# Check read operation
data = sheets.read_sheet(spreadsheet_id, "Sheet1")
if data is None:
    logger.error("Failed to read - check spreadsheet ID and permissions")
elif len(data) == 0:
    logger.warning("Sheet is empty")
else:
    logger.info(f"Read {len(data)} rows")

# Check write operation
if not sheets.write_sheet(spreadsheet_id, "Sheet1!A1", data):
    logger.error("Failed to write - check permissions and quota")
```

## Troubleshooting

### "Authentication failed"
- Ensure `google_credentials.json` exists
- Delete `token.pickle` and re-authenticate
- Verify Google Sheets API is enabled

### "HTTP 404: Requested entity was not found"
- Check spreadsheet ID is correct
- Verify you have access to the spreadsheet
- Ensure sheet/tab name exists

### "HTTP 403: The caller does not have permission"
- Spreadsheet must be owned by or shared with authenticated user
- Check OAuth scopes include Sheets access
- Re-authenticate with correct permissions

### "No data found"
- Range may be empty
- Check A1 notation is correct
- Verify sheet name is correct

### "Invalid range"
- Check A1 notation syntax
- Sheet name may need quotes if it contains spaces: "'My Sheet'!A1"

## Permissions

The connector uses the `spreadsheets` scope, which allows:
- ✓ Read spreadsheets
- ✓ Write to spreadsheets
- ✓ Create/delete sheets
- ✓ Format cells
- ✗ Delete spreadsheets (requires broader scope)

## Best Practices

1. **Batch Operations**: Use `batch_update()` for multiple ranges
2. **Error Handling**: Always check return values
3. **Rate Limits**: Be aware of Google API quotas (100 requests/100 seconds per user)
4. **Clear Before Write**: Use `clear_sheet()` before `write_sheet()` for full replacement
5. **Headers**: Keep headers in row 1 for easy filtering
6. **Date Format**: Use ISO format (YYYY-MM-DD) for consistent sorting
7. **Value Types**: Use "USER_ENTERED" for dates/formulas, "RAW" for plain text

## Integration with Transaction Model

```python
from src.models import Transaction
from src.connectors import GoogleSheetsConnector

def write_transactions(transactions, spreadsheet_id, tab_name="Transactions"):
    """Write Transaction objects to Google Sheets."""

    sheets = GoogleSheetsConnector(creds_path, token_path)
    sheets.authenticate()

    # Create tab if needed
    sheets.create_tab(spreadsheet_id, tab_name)

    # Prepare headers
    headers = Transaction.get_header()

    # Convert transactions to rows
    rows = [headers]
    for txn in transactions:
        rows.append(list(txn.to_dict().values()))

    # Write to sheet
    return sheets.write_sheet(spreadsheet_id, f"{tab_name}!A1", rows)
```

## Next Steps

With both Drive and Sheets connectors complete:
1. Test both connectors with your Google account
2. Implement file parsers (`src/core/parser.py`)
3. Implement data normalizer (`src/core/normalizer.py`)
4. Create the main orchestration (`src/main.py`)
