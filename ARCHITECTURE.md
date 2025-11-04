# Finance Consolidator - Architecture Overview

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                          GOOGLE DRIVE                               │
│                                                                     │
│  📁 Input Folder                                                    │
│    ├── csob_export_pohyby_283337817.csv         (ČSOB Credit Card)│
│    ├── csob_export_pohyby_210621040.csv         (ČSOB Account)    │
│    ├── vypis_3581422554_20251001_20251031.xlsx  (Partners #1)     │
│    ├── vypis_1330299329_20251001_20251031.xlsx  (Partners #2)     │
│    ├── vypis_2106210400_20251001_20251031.xlsx  (Partners #3)     │
│    └── transaction-history.csv                   (Wise)            │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Google Drive API
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FILE SCANNER                                     │
│  1. List files in Drive folder                                      │
│  2. Match filenames to institution patterns                         │
│  3. Download files to temp location                                 │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Files
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         PARSER                                      │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ ČSOB Parser  │  │Partners      │  │ Wise Parser  │             │
│  │              │  │Parser        │  │              │             │
│  │• Skip 2 rows │  │• Read XLSX   │  │• Standard CSV│             │
│  │• UTF-8-sig   │  │• Concat cols │  │• Handle      │             │
│  │• Semicolon ; │  │• Split by ;  │  │  Direction   │             │
│  │• Date: d.m.Y │  │• Extract acc │  │• Filter      │             │
│  │• Amount:     │  │• Date:       │  │  Status      │             │
│  │  1 000,00    │  │  d. m. Y     │  │• Amount:     │             │
│  └──────────────┘  └──────────────┘  │  1234.56     │             │
│                                       └──────────────┘             │
│                                                                     │
│  Output: List of raw transaction dicts                             │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Raw data
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      NORMALIZER                                     │
│                                                                     │
│  For each raw transaction:                                          │
│  1. Parse date → datetime                                           │
│  2. Parse amount → Decimal                                          │
│  3. Normalize currency code (CZK/EUR)                               │
│  4. Convert to EUR (CZK * 0.04)                                     │
│  5. Map category (institution → standard)                           │
│  6. Determine owner (from config)                                   │
│  7. Generate transaction_id                                         │
│  8. Create Transaction object                                       │
│                                                                     │
│  Output: List of Transaction objects                                │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Transaction objects
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         WRITER                                      │
│                                                                     │
│  1. Convert Transaction objects to rows                             │
│  2. Format for Google Sheets                                        │
│  3. Append to Transactions tab                                      │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Google Sheets API
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      GOOGLE SHEETS                                  │
│                                                                     │
│  📊 Master Spreadsheet                                              │
│    ├── Transactions Tab                                             │
│    │   Columns: transaction_id, date, description, amount,         │
│    │            currency, amount_eur, category, account,           │
│    │            institution, owner, type, ...                      │
│    │                                                                │
│    └── Balances Tab (future)                                        │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Interactions

```
┌──────────────────┐
│   main.py        │  Entry point
│                  │
│  Orchestrates:   │
│  • Load configs  │
│  • Init logger   │───────┐
│  • Init currency │       │
│  • Scan files    │       │
│  • Parse files   │       │
│  • Normalize     │       │
│  • Write output  │       │
└────────┬─────────┘       │
         │                 │
         │                 │
         ├─────────────────┼─────────────────────────┐
         │                 │                         │
         ▼                 ▼                         ▼
┌────────────────┐ ┌────────────────┐     ┌────────────────┐
│ Google Drive   │ │ Google Sheets  │     │ File Scanner   │
│ Connector      │ │ Connector      │     │                │
│                │ │                │     │ Uses:          │
│• authenticate  │ │• authenticate  │     │ • Drive API    │
│• list_files    │ │• read_sheet    │     │ • Inst configs │
│• download_file │ │• write_sheet   │     └────────────────┘
└────────────────┘ │• append_sheet  │              │
         │         └────────────────┘              │
         │                  │                      │
         ▼                  ▼                      ▼
┌────────────────────────────────────────────────────────┐
│                    Core Processing                     │
│                                                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ Parser   │  │Normalizer│  │ Writer   │            │
│  │          │  │          │  │          │            │
│  │Parse CSV │→ │Convert to│→ │Write to  │            │
│  │/XLSX     │  │Transaction│  │Sheets    │            │
│  └──────────┘  └──────────┘  └──────────┘            │
│       ▲              ▲              ▲                 │
│       │              │              │                 │
│       └──────────────┴──────────────┘                 │
│              Uses utilities:                          │
│         ┌──────────────────────┐                      │
│         │ • Date Parser        │                      │
│         │ • Currency Converter │                      │
│         │ • Logger             │                      │
│         └──────────────────────┘                      │
└────────────────────────────────────────────────────────┘
```

## Configuration Structure

```
config/
│
├── settings.yaml                    # Main settings
│   ├── google_drive                 # Drive API settings
│   ├── google_sheets                # Sheets API settings
│   ├── currency                     # Exchange rates
│   ├── processing                   # Processing options
│   └── logging                      # Log settings
│
└── institutions/                    # Institution-specific configs
    │
    ├── csob.yaml                    # ČSOB Configuration
    │   ├── institution              # Name, type
    │   ├── file_detection           # Filename patterns
    │   ├── csv_format               # Encoding, delimiter
    │   ├── column_mapping           # CSV columns → fields
    │   ├── transformations          # Date/amount parsing
    │   ├── owner_detection          # Account → owner mapping
    │   └── category_mapping         # Category translation
    │
    ├── partners.yaml                # Partners Bank Config
    │   └── (same structure)
    │
    └── wise.yaml                    # Wise Config
        └── (same structure)
```

## Data Model

```
Transaction
├── transaction_id: str              (Auto-generated: TXN_20241015_001)
├── date: datetime                   (Parsed from source)
├── description: str                 (From CSV or counterparty name)
├── amount: Decimal                  (Original amount)
├── currency: str                    (CZK/EUR)
├── amount_eur: Decimal              (Normalized amount)
├── category: str                    (Mapped category)
├── account: str                     (Account number)
├── institution: str                 (ČSOB/Partners/Wise)
├── owner: str                       (Branislav/etc.)
├── transaction_type: str            (Debit/Credit/Transfer)
├── counterparty_account: str        (Optional)
├── counterparty_name: str           (Optional)
├── counterparty_bank: str           (Optional)
├── reference: str                   (Optional)
├── variable_symbol: str             (Optional)
├── constant_symbol: str             (Optional)
├── specific_symbol: str             (Optional)
├── note: str                        (Optional)
├── exchange_rate: Decimal           (Optional)
├── source_file: str                 (Original filename)
└── processed_date: datetime         (When added to system)
```

## Institution-Specific Parsing Logic

### ČSOB
```
File: csob_export_pohyby_283337817.csv
├── Line 1: "Pohyby na účtu..." → SKIP
├── Line 2: (empty) → SKIP
├── Line 3: Headers → READ
│   číslo účtu;datum zaúčtování;částka;měna;...
└── Line 4+: Data
    283337817/0300;31.10.2025;-1100,00;CZK;...
    
Processing:
1. Skip first 2 lines
2. Read with encoding='utf-8-sig' (BOM)
3. Parse semicolon-delimited
4. Amount: remove space thousands, comma→period
5. Date: %d.%m.%Y
6. Owner: from account_mapping
```

### Partners Bank
```
File: vypis_1330299329_20251001_20251031.xlsx
├── Row 1: Headers (all in cell A1)
└── Row 2+: Data (split across A, B, C, D)

Cell A2: "1. 10. 2025;...;-1 000"
Cell B2: "00";..."CZK";"-764"
Cell C3: "00";..."CZK";"1"...
Cell D4: (continuation)

Processing:
1. Open XLSX with openpyxl
2. For each row: concatenate A+B+C+D
3. Split by semicolon
4. Extract account from filename: vypis_(\d+)_
5. Parse date: %d. %m. %Y
6. Amount: remove space, comma→period
```

### Wise
```
File: transaction-history.csv
Header: ID,Status,Direction,Created on,...
Data: CARD_TRANSACTION-3081510277,COMPLETED,OUT,2025-11-03 21:51:17,...

Processing:
1. Standard CSV (comma delimiter)
2. Filter: Status == "COMPLETED"
3. Amount sign: OUT=negative, IN=positive
4. Description: OUT→Target name, IN→Source name
5. Date: %Y-%m-%d %H:%M:%S
6. Owner: fixed (from config)
```

## Output Format (Google Sheets)

### Transactions Tab
```
Row 1 (Headers):
transaction_id | date | description | amount | currency | amount_eur | ...

Row 2 (Example):
TXN_20241031_001 | 2024-10-31 | PORTO RESTAURANT | -1100.00 | CZK | -44.00 | ...

Features:
• Sortable by date
• Filterable by owner, institution, category
• Standardized format across all sources
• Original currency preserved
• Normalized EUR amount for totals
```

## Error Handling

```
Each layer handles errors:

Parser
└── Catches: encoding errors, malformed CSV
    └── Logs: warning, skips row, continues

Normalizer
└── Catches: invalid amounts, dates, missing fields
    └── Logs: warning, uses defaults or None

Writer
└── Catches: Google API errors, quota exceeded
    └── Logs: error, retries with backoff

Main
└── Catches: all exceptions
    └── Logs: critical error, exits gracefully
```

## Summary

- **3 Institutions** → 3 different parsers
- **All data** → 1 normalized format
- **1 Google Sheet** → Single source of truth
- **Flexible** → Easy to add new institutions
- **Configurable** → YAML configs, no code changes needed
- **Family-friendly** → Track multiple owners
- **Multi-currency** → CZK & EUR with normalization
