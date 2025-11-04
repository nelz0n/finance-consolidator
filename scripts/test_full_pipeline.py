"""Test full pipeline: parse → normalize → write to Sheets."""

import sys
from pathlib import Path
import yaml

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.connectors import GoogleDriveConnector, GoogleSheetsConnector
from src.core import FileParser, DataNormalizer, SheetsWriter
from src.utils import CurrencyConverter, setup_logger


def load_institution_configs(config_dir: str = "config/institutions") -> dict:
    """Load all institution configurations."""
    configs = {}
    config_path = Path(config_dir)

    for yaml_file in config_path.glob("*.yaml"):
        with open(yaml_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            inst_name = config.get('institution', {}).get('name', yaml_file.stem)
            configs[inst_name] = config

    return configs


def main():
    """Test full pipeline."""

    # Setup logger
    global logger
    logger = setup_logger(level='INFO', console=True)

    logger.info("="*70)
    logger.info("FULL PIPELINE TEST: PARSE → NORMALIZE → WRITE TO SHEETS")
    logger.info("="*70)

    # Load configs
    with open('config/settings.yaml', 'r') as f:
        settings = yaml.safe_load(f)

    institution_configs = load_institution_configs()

    # Initialize components
    logger.info("\n1. Initializing components...")

    # Currency converter
    converter = CurrencyConverter(
        rates=settings['currency']['rates'],
        base_currency=settings['currency']['base_currency']
    )
    logger.info("   ✅ Currency converter initialized")

    # Drive connector
    drive = GoogleDriveConnector(
        settings['google_drive']['credentials_path'],
        settings['google_drive']['token_path']
    )
    if not drive.authenticate():
        logger.error("Failed to authenticate with Drive")
        return
    logger.info("   ✅ Google Drive connector authenticated")

    # Sheets connector
    sheets = GoogleSheetsConnector(
        settings['google_drive']['credentials_path'],
        settings['google_drive']['token_path']
    )
    if not sheets.authenticate():
        logger.error("Failed to authenticate with Sheets")
        return
    logger.info("   ✅ Google Sheets connector authenticated")

    # Writer
    writer = SheetsWriter(sheets, settings['google_sheets']['master_sheet_id'])
    logger.info("   ✅ SheetsWriter initialized")

    # Prepare
    folder_id = settings['google_drive']['input_folder_id']
    temp_dir = Path("data/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Test with one file from each institution
    institutions_to_test = [
        ('ČSOB', 'csob_*.csv'),
        ('Partners Bank', 'vypis_*.xlsx'),
        ('Wise', 'transaction-history*.csv')
    ]

    all_transactions = []

    logger.info("\n2. Processing files...")

    for inst_name, pattern in institutions_to_test:
        logger.info(f"\n   Processing {inst_name}...")

        # Find files
        files = drive.list_files(folder_id, file_pattern=pattern)
        if not files:
            logger.warning(f"   ⚠️  No files found for {inst_name}")
            continue

        # Get first file
        test_file = files[0]
        logger.info(f"   File: {test_file['name']}")

        # Download
        local_path = temp_dir / test_file['name']
        if not drive.download_file(test_file['id'], str(local_path)):
            logger.error(f"   ❌ Failed to download")
            continue

        # Get config
        inst_config = institution_configs.get(inst_name)
        if not inst_config:
            logger.error(f"   ❌ No config for {inst_name}")
            continue

        # Parse
        parser = FileParser(inst_config)
        raw_transactions = parser.parse_file(str(local_path))
        logger.info(f"   ✅ Parsed {len(raw_transactions)} raw transactions")

        # Normalize
        normalizer = DataNormalizer(converter, inst_config)
        transactions = normalizer.normalize_transactions(
            raw_transactions,
            test_file['name']
        )
        logger.info(f"   ✅ Normalized {len(transactions)} transactions")

        all_transactions.extend(transactions)

    # Summary
    logger.info(f"\n3. Summary:")
    logger.info(f"   Total transactions: {len(all_transactions)}")

    if all_transactions:
        total_eur = sum(t.amount_eur for t in all_transactions if t.amount_eur)
        logger.info(f"   Total value: {total_eur:.2f} EUR")

        # Group by institution
        by_institution = {}
        for txn in all_transactions:
            if txn.institution not in by_institution:
                by_institution[txn.institution] = []
            by_institution[txn.institution].append(txn)

        logger.info(f"\n   Breakdown:")
        for inst, txns in by_institution.items():
            inst_total = sum(t.amount_eur for t in txns if t.amount_eur)
            logger.info(f"     {inst}: {len(txns)} transactions, {inst_total:.2f} EUR")

    # Write to Sheets
    logger.info(f"\n4. Writing to Google Sheets...")
    logger.info(f"   Spreadsheet: {settings['google_sheets']['master_sheet_id']}")
    logger.info(f"   Tab: {settings['google_sheets']['transactions_tab']}")

    # Ask user for confirmation
    logger.info("\n   ⚠️  This will write data to your Google Sheet!")
    response = input("   Continue? (yes/no): ").strip().lower()

    if response != 'yes':
        logger.info("   Cancelled by user")
        return

    # Write transactions
    success = writer.write_transactions(
        all_transactions,
        tab_name=settings['google_sheets']['transactions_tab'],
        mode='append'  # Append to existing data
    )

    if success:
        logger.info("\n✅ SUCCESS! Data written to Google Sheets")
        logger.info(f"\nView your data:")
        sheet_id = settings['google_sheets']['master_sheet_id']
        logger.info(f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit")
    else:
        logger.error("\n❌ FAILED to write data")

    logger.info("\n" + "="*70)
    logger.info("TEST COMPLETE")
    logger.info("="*70)


if __name__ == "__main__":
    main()
