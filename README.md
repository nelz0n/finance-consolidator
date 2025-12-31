# Finance Consolidator

A comprehensive personal finance management application that aggregates banking and investment data from multiple Czech financial institutions into a unified SQLite database with an intuitive web interface.

## Features

### 🏦 Multi-Institution Support
- **ČSOB Bank** - Czech savings and checking accounts
- **Partners Bank** - Investment accounts and portfolios
- **Wise** - Multi-currency international transfers
- Easy to add new institutions via YAML configuration

### 💰 Transaction Management
- **Centralized Database** - All transactions in SQLite for fast querying
- **Multi-Currency Support** - Automatic conversion to CZK using CNB API or static rates
- **Smart Categorization** - 3-tier category hierarchy with manual rules and AI fallback
- **Duplicate Detection** - Hash-based transaction IDs prevent duplicate imports
- **Bulk Operations** - Select, delete, and update multiple transactions

### 📊 Web Interface
- **Modern UI** - Clean Svelte-based interface with responsive design
- **Advanced Filtering** - By date, institution, category, amount, search text
- **Customizable Columns** - Show/hide and reorder columns with drag-and-drop
- **Inline Editing** - Quick category changes with cascading dropdowns
- **Mass Selection** - Select all filtered transactions across pages
- **Export** - CSV and Excel export with full Unicode support

### 🎯 Categorization System
- **3-Tier Hierarchy** - Tier1 > Tier2 > Tier3 categories
- **Rule-Based** - Pattern matching on description, counterparty, amount
- **AI Fallback** - Gemini AI categorization with confidence scores
- **Rate Limiting** - Smart rate limiting (10 req/min, 1000/day)
- **Historical Context** - AI learns from previously categorized transactions

### 🔧 Developer-Friendly
- **Config-Driven** - Add new institutions without code changes
- **Well-Documented** - Comprehensive CLAUDE.md and ARCHITECTURE.md
- **Type Safety** - Python type hints and Pydantic models
- **Logging** - Detailed logs for debugging and monitoring

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/finance-consolidator.git
cd finance-consolidator
```

2. **Set up Python environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Set up Frontend**
```bash
cd frontend
npm install
cd ..
```

4. **Configure Settings**
- Copy `config/settings.yaml.example` to `config/settings.yaml` (if needed)
- Edit `config/settings.yaml` to set your currency preferences
- Configure institution parsers in `config/institutions/`

5. **Run the Application**

Start the backend (in one terminal):
```bash
uvicorn backend.app:app --reload --port 8000
```

Start the frontend (in another terminal):
```bash
cd frontend
npm run dev
```

6. **Access the Application**
- Web UI: http://localhost:5173
- API Docs: http://localhost:8000/docs

## Usage

### Uploading Bank Statements

1. Navigate to the **File Upload** page
2. Select your institution (ČSOB, Partners Bank, or Wise)
3. Choose your CSV/XLSX file
4. Click **Upload**
5. Monitor processing progress in real-time
6. View transactions in the **Transactions** page

### Managing Transactions

**Filtering:**
- Use date range, institution, category filters
- Search by description or counterparty
- Filter by amount range or transaction type

**Bulk Operations:**
- Click **Select** to enter selection mode
- Click **Select All Filtered** to select all matching transactions
- Click **Delete Selected** to remove transactions

**Editing:**
- Double-click category cells for inline editing
- Click edit icon for full transaction details
- Changes are saved immediately

### Categorization Rules

1. Navigate to **Rules** page
2. Click **Add Rule**
3. Define conditions (description contains, amount range, etc.)
4. Set target category (Tier1 > Tier2 > Tier3)
5. Set priority (higher = applied first)
6. Save and test the rule

### Adding New Institutions

Use the interactive wizard:
```bash
python scripts/add_institution.py
```

Or manually create a YAML config in `config/institutions/`:
```yaml
institution:
  name: "My Bank"
  code: "mybank"
  type: "bank"

file_detection:
  filename_patterns:
    - "mybank_*.csv"

csv_format:
  encoding: "utf-8"
  delimiter: ","
  skip_rows: 0
  has_header: true

column_mapping:
  date: "Transaction Date"
  amount: "Amount"
  currency: "Currency"
  description: "Description"

transformations:
  date:
    format: "%Y-%m-%d"
  amount:
    decimal_separator: "."
    thousands_separator: ","
```

## Project Structure

```
finance-consolidator/
├── backend/              # FastAPI backend
│   ├── api/              # API endpoints
│   ├── database/         # SQLAlchemy models & repos
│   └── schemas/          # Pydantic schemas
├── frontend/             # Svelte frontend
│   └── src/
│       ├── routes/       # Page components
│       └── lib/          # Shared utilities
├── src/                  # Core processing logic
│   ├── core/             # Parser, normalizer, writer
│   ├── models/           # Transaction models
│   └── utils/            # Currency, categorizer, logger
├── config/               # Configuration files
│   ├── institutions/     # Institution parsers
│   ├── settings.yaml     # Global settings
│   └── accounts.yaml     # Account descriptions
├── data/                 # Data directory (gitignored)
│   ├── finance.db        # SQLite database
│   ├── logs/             # Application logs
│   └── uploads/          # Uploaded files
└── scripts/              # Utility scripts
```

## Configuration

### Currency Conversion

Edit `config/settings.yaml`:

```yaml
currency:
  base_currency: "CZK"
  use_cnb_api: true  # Use Czech National Bank API for real rates

  # Fallback rates if API fails
  rates:
    CZK: 1.0
    EUR: 24.5
    USD: 22.8
    GBP: 28.5
```

### AI Categorization

The system uses Google's Gemini AI for uncategorized transactions. To enable:

1. Get API key from https://aistudio.google.com/
2. Set environment variable:
```bash
export GEMINI_API_KEY="your-api-key"
```

3. AI features:
   - Rate limited to 10 requests/minute, 1000/day
   - Learns from historical categorizations
   - Provides confidence scores
   - Can be disabled per-upload

## API Documentation

Once running, visit http://localhost:8000/docs for interactive API documentation.

Key endpoints:
- `GET /api/v1/transactions` - List transactions with filters
- `POST /api/v1/files/upload` - Upload bank statement
- `GET /api/v1/categories/tree` - Get category hierarchy
- `POST /api/v1/rules` - Create categorization rule

## Development

### Running Tests
```bash
pytest tests/
```

### Code Style
```bash
black src/ backend/
flake8 src/ backend/
```

### Database Migrations
```bash
# Reset database (WARNING: deletes all data)
rm data/finance.db
python -c "from backend.database.connection import init_db; init_db()"
```

## Troubleshooting

**Upload fails with "Currency EUR not in rates"**
- Ensure backend server was restarted after updating settings.yaml
- Check that CNB API is enabled or fallback rates are configured

**Frontend shows old data**
- Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
- Clear browser cache

**AI categorization not working**
- Check GEMINI_API_KEY environment variable is set
- Verify rate limits haven't been exceeded (check logs)

## Security Notes

**Never commit sensitive data:**
- `data/` directory (contains transaction database)
- `*.db` files (SQLite databases)
- `.env` files (API keys)
- Actual bank statements (CSV/XLSX files)

The `.gitignore` is pre-configured to exclude these.

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation in `CLAUDE.md` and `ARCHITECTURE.md`

## Acknowledgments

- Built with FastAPI, Svelte, SQLAlchemy
- Currency rates from Czech National Bank (CNB)
- AI categorization powered by Google Gemini
