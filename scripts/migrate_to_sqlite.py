"""
Migration script: Import existing data from Google Sheets to SQLite database.

Usage:
    python scripts/migrate_to_sqlite.py
"""
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from decimal import Decimal
import hashlib
from backend.database.connection import init_db, get_db_context
from backend.database.models import Institution, Owner, Account, Transaction
from src.connectors.google_sheets import GoogleSheetsConnector
from src.utils.logger import setup_logger
import yaml

logger = setup_logger(level="INFO", console=True)


def load_config():
    """Load configuration"""
    with open("config/settings.yaml", 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def parse_amount(value_str):
    """Parse amount string handling European comma decimal separator"""
    if not value_str or str(value_str).strip() == '':
        return Decimal('0')

    # Convert to string and handle European format (comma as decimal separator)
    value_str = str(value_str).strip()
    value_str = value_str.replace(',', '.')

    try:
        return Decimal(value_str)
    except:
        return Decimal('0')


def generate_transaction_id(date, amount, currency, description, account='', **kwargs):
    """Generate hash-based transaction ID (same as normalizer)"""
    date_str = date.strftime('%Y%m%d') if isinstance(date, datetime) else str(date)

    # Build hash parts
    hash_parts = [date_str, str(amount), currency, account, description]

    # Add optional fields if available
    for field in ['counterparty_account', 'counterparty_name', 'variable_symbol',
                  'constant_symbol', 'specific_symbol', 'reference', 'note']:
        value = kwargs.get(field, '')
        if value and str(value).strip():
            hash_parts.append(str(value).strip())

    # Generate hash
    hash_input = '|'.join(hash_parts)
    hash_obj = hashlib.sha256(hash_input.encode('utf-8'))
    hash_hex = hash_obj.hexdigest()[:8]

    return f"TXN_{date_str}_{hash_hex}"


def migrate_institutions(db, config):
    """Create institution records"""
    logger.info("Creating institutions...")

    institutions = [
        {"code": "csob", "name": "ČSOB", "type": "bank", "country": "CZ"},
        {"code": "partners", "name": "Partners Bank", "type": "bank", "country": "CZ"},
        {"code": "wise", "name": "Wise", "type": "bank", "country": "GB"},
    ]

    inst_map = {}
    for inst_data in institutions:
        inst = db.query(Institution).filter(Institution.code == inst_data["code"]).first()
        if not inst:
            inst = Institution(**inst_data)
            db.add(inst)
            db.flush()
            logger.info(f"Created institution: {inst.name}")
        inst_map[inst.code] = inst.id

    db.commit()
    return inst_map


def migrate_from_sheets(db, sheets, config, inst_map):
    """Migrate transactions from Google Sheets"""
    logger.info("Reading transactions from Google Sheets...")

    spreadsheet_id = config['google_sheets']['master_sheet_id']
    transactions_tab = config['google_sheets']['transactions_tab']

    # Read all data
    data = sheets.read_sheet(spreadsheet_id, f"{transactions_tab}!A:Z")

    if not data:
        logger.warning("No data found in Google Sheets")
        return

    headers = data[0]
    rows = data[1:]

    logger.info(f"Found {len(rows)} transactions to migrate")

    # Create owner and account mappings
    owners_map = {}
    accounts_map = {}

    # Process transactions
    migrated = 0
    skipped = 0

    for i, row in enumerate(rows, start=2):
        if not row or len(row) < 5:  # Skip empty rows
            continue

        try:
            # Parse row (adjust indices based on your sheet structure)
            date_str = row[1] if len(row) > 1 else None
            description = row[2] if len(row) > 2 else ""
            amount_str = row[3] if len(row) > 3 else "0"
            currency = row[4] if len(row) > 4 else "CZK"

            # Parse amount using helper function
            amount = parse_amount(amount_str)

            # Parse date
            if date_str:
                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    date = datetime.now()
            else:
                date = datetime.now()

            # Get additional fields for hash generation
            account = row[5] if len(row) > 5 else ""
            counterparty_account = row[6] if len(row) > 6 else ""
            counterparty_name = row[7] if len(row) > 7 else ""
            variable_symbol = row[12] if len(row) > 12 else ""
            constant_symbol = row[13] if len(row) > 13 else ""
            specific_symbol = row[14] if len(row) > 14 else ""

            # Generate hash-based transaction ID
            txn_id = generate_transaction_id(
                date=date,
                amount=amount,
                currency=currency,
                description=description,
                account=account,
                counterparty_account=counterparty_account,
                counterparty_name=counterparty_name,
                variable_symbol=variable_symbol,
                constant_symbol=constant_symbol,
                specific_symbol=specific_symbol
            )

            # Skip if transaction already exists
            existing = db.query(Transaction).filter(Transaction.transaction_id == txn_id).first()
            if existing:
                skipped += 1
                continue

            # Create transaction
            transaction = Transaction(
                transaction_id=txn_id,
                date=date,
                description=description,
                amount=float(amount),
                currency=currency,
                amount_czk=float(amount),  # Simplified for migration
                processed_date=datetime.now()
            )

            db.add(transaction)
            migrated += 1

            if migrated % 100 == 0:
                db.flush()
                logger.info(f"Migrated {migrated} transactions...")

        except Exception as e:
            logger.error(f"Error migrating row {i}: {e}")
            db.rollback()  # Rollback on error and continue
            continue

    db.commit()
    logger.info(f"Migration complete: {migrated} migrated, {skipped} skipped")


def main():
    """Main migration function"""
    logger.info("=" * 80)
    logger.info("Migration: Google Sheets → SQLite")
    logger.info("=" * 80)

    # Load config
    config = load_config()

    # Initialize database
    logger.info("Initializing database...")
    init_db()

    # Initialize Google Sheets connector
    logger.info("Connecting to Google Sheets...")
    sheets = GoogleSheetsConnector(
        credentials_path=config['google_drive']['credentials_path'],
        token_path=config['google_drive']['token_path']
    )

    if not sheets.authenticate():
        logger.error("Failed to authenticate with Google Sheets")
        return 1

    # Perform migration
    with get_db_context() as db:
        # Migrate institutions
        inst_map = migrate_institutions(db, config)

        # Migrate transactions
        migrate_from_sheets(db, sheets, config, inst_map)

    logger.info("=" * 80)
    logger.info("Migration completed successfully!")
    logger.info("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
