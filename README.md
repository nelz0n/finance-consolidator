# Finance Consolidation Tool

Consolidate banking and investment data from multiple Czech institutions (ČSOB, Partners Bank, Wise) into a single Google Sheets master file.

## Features

- **Multi-institution support**: ČSOB, Partners Bank, Wise (easily extensible)
- **Flexible configuration**: YAML-based institution configs
- **Multi-currency**: Supports CZK and EUR with normalization
- **Family tracking**: Track transactions by owner
- **Google Drive integration**: Read CSVs from Drive, write to Sheets
- **Transaction & Balance tracking**: Comprehensive financial data

## Quick Start

### 1. Prerequisites

```bash
# Python 3.8+
python --version

# Git
git --version
```

### 2. Clone and Setup

```bash
git clone <your-repo-url>
cd finance-consolidator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Google API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable APIs:
   - Google Drive API
   - Google Sheets API
4. Create credentials (OAuth 2.0 Client ID for Desktop app)
5. Download credentials JSON
6. Save as `data/credentials/google_credentials.json`

### 4. Configuration

```bash
# Copy example config
cp config/settings.yaml.example config/settings.yaml

# Edit with your details
nano config/settings.yaml
```

Update `config/settings.yaml`:
```yaml
google_drive:
  input_folder_id: "your-drive-folder-id"  # Where CSV files are stored
  
google_sheets:
  master_sheet_id: "your-sheet-id"  # Master data sheet
  transactions_tab: "Transactions"
  balances_tab: "Balances"
```

### 5. Run

```bash
# Process all new files
python -m src.main

# Dry run (see what would be processed)
python -m src.main --dry-run

# Process specific institution
python -m src.main --institution csob

# Process date range
python -m src.main --from-date 2024-10-01 --to-date 2024-10-31
```

## File Structure

```
finance-consolidator/
├── config/
│   ├── institutions/      # Institution-specific configs
│   │   ├── csob.yaml
│   │   ├── partners.yaml
│   │   └── wise.yaml
│   └── settings.yaml      # General settings
├── src/
│   ├── core/             # Core processing logic
│   ├── connectors/       # Google API connectors
│   ├── utils/            # Utilities
│   └── models/           # Data models
├── scripts/              # Helper scripts
└── data/                 # Local data (not in git)
```

## Institution Configuration

Each institution has a YAML config in `config/institutions/`. Example:

```yaml
institution:
  name: "ČSOB"
  type: "bank"
  
file_detection:
  filename_patterns:
    - "csob_export_pohyby_*.csv"

csv_format:
  encoding: "utf-8-sig"
  delimiter: ";"
  has_header: true
  skip_rows: 2

column_mapping:
  date: "datum zaúčtování"
  description: "zpráva"
  amount: "částka"
  currency: "měna"
  # ... more fields
```

## Adding New Institution

```bash
# Interactive wizard
python scripts/add_institution.py

# Test configuration
python scripts/test_config.py --institution new_bank --file sample.csv
```

## Master Data Schema

### Transactions
- transaction_id, date, description, amount, currency, amount_eur
- category, account, institution, owner, type
- source_file, processed_date

### Balances
- balance_id, date, account, institution, owner
- asset_type, asset_name, quantity, price, value
- currency, value_eur, source_file, processed_date

## Usage Examples

```bash
# Monthly update
python -m src.main --from-date 2024-10-01 --to-date 2024-10-31

# Process only ČSOB
python -m src.main --institution csob

# Verbose logging
python -m src.main --verbose

# Force reprocess (overwrite existing)
python -m src.main --force
```

## Troubleshooting

### "No credentials found"
- Ensure `data/credentials/google_credentials.json` exists
- Run `python scripts/setup_credentials.py` for help

### "File not found in Drive"
- Check `input_folder_id` in `config/settings.yaml`
- Verify file permissions in Google Drive

### "Parsing error"
- Test config: `python scripts/test_config.py --institution <name> --file <path>`
- Check encoding, delimiter in institution config

### "Currency conversion failed"
- Ensure currency codes are correct (CZK, EUR)
- Check exchange rate source in settings

## Security Notes

⚠️ **Never commit to git:**
- `data/credentials/google_credentials.json`
- `data/` directory (contains sensitive data)
- `.env` files

## Future Enhancements

- [ ] Duplicate detection
- [ ] Automated scheduling (cron/scheduler)
- [ ] ML-based category suggestions
- [ ] Historical exchange rates
- [ ] Web interface
- [ ] Email notifications

## Support

For issues, check:
1. Logs in `data/logs/`
2. GitHub Issues
3. Configuration examples in `config/institutions/`

## License

MIT License - feel free to modify and extend!
