"""Test script for parser + normalizer pipeline."""

import sys
from pathlib import Path
import yaml

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.connectors import GoogleDriveConnector
from src.core.parser import FileParser
from src.core.normalizer import DataNormalizer
from src.utils.currency import CurrencyConverter
from src.utils.logger import setup_logger


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
    """Test full pipeline: parse + normalize."""

    # Setup logger
    global logger
    logger = setup_logger(level='INFO', console=True)

    logger.info("="*70)
    logger.info("PARSER + NORMALIZER TEST")
    logger.info("="*70)

    # Load configs
    with open('config/settings.yaml', 'r') as f:
        settings = yaml.safe_load(f)

    institution_configs = load_institution_configs()

    # Initialize currency converter
    logger.info("\nInitializing currency converter...")
    converter = CurrencyConverter(
        rates=settings['currency']['rates'],
        base_currency=settings['currency']['base_currency']
    )
    logger.info(f"Base currency: {settings['currency']['base_currency']}")
    logger.info(f"Exchange rates: {settings['currency']['rates']}")

    # Initialize Drive connector
    drive = GoogleDriveConnector(
        settings['google_drive']['credentials_path'],
        settings['google_drive']['token_path']
    )

    if not drive.authenticate():
        logger.error("Failed to authenticate")
        return

    folder_id = settings['google_drive']['input_folder_id']
    temp_dir = Path("data/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Test each institution
    institutions_to_test = [
        ('ČSOB', 'csob_*.csv', 1),
        ('Partners Bank', 'vypis_*.xlsx', 1),
        ('Wise', 'transaction-history*.csv', 1)
    ]

    all_transactions = []

    for inst_name, pattern, limit in institutions_to_test:
        logger.info("\n" + "="*70)
        logger.info(f"TESTING {inst_name}")
        logger.info("="*70)

        # Find files
        files = drive.list_files(folder_id, file_pattern=pattern)

        if not files:
            logger.warning(f"No files found for {inst_name}")
            continue

        # Get first file
        test_file = files[0]
        logger.info(f"\nFile: {test_file['name']}")

        # Download
        local_path = temp_dir / test_file['name']
        if not drive.download_file(test_file['id'], str(local_path)):
            logger.error(f"Failed to download")
            continue

        # Get config
        inst_config = institution_configs.get(inst_name)
        if not inst_config:
            logger.error(f"No config for {inst_name}")
            continue

        # PARSE
        logger.info(f"\n1. Parsing...")
        parser = FileParser(inst_config)
        raw_transactions = parser.parse_file(str(local_path))
        logger.info(f"   ✅ Parsed {len(raw_transactions)} raw transactions")

        # NORMALIZE
        logger.info(f"\n2. Normalizing...")
        normalizer = DataNormalizer(converter, inst_config)
        transactions = normalizer.normalize_transactions(
            raw_transactions,
            test_file['name']
        )
        logger.info(f"   ✅ Normalized {len(transactions)} transactions")

        # Show samples
        if transactions:
            logger.info(f"\n3. Sample transactions:")
            for i, txn in enumerate(transactions[:3], 1):
                logger.info(f"\n   Transaction {i}:")
                logger.info(f"     ID: {txn.transaction_id}")
                logger.info(f"     Date: {txn.date.strftime('%Y-%m-%d')}")
                logger.info(f"     Description: {txn.description[:50]}...")
                logger.info(f"     Amount: {txn.amount} {txn.currency}")
                logger.info(f"     Amount EUR: {txn.amount_eur}")
                logger.info(f"     Category: {txn.category}")
                logger.info(f"     Owner: {txn.owner}")
                logger.info(f"     Type: {txn.transaction_type}")

            # Statistics
            logger.info(f"\n4. Statistics:")
            logger.info(f"     Total: {len(transactions)}")

            total_amount = sum(t.amount for t in transactions)
            logger.info(f"     Total amount: {total_amount} (local currency)")

            total_eur = sum(t.amount_eur for t in transactions if t.amount_eur)
            logger.info(f"     Total EUR: {total_eur:.2f}")

            owners = set(t.owner for t in transactions)
            logger.info(f"     Owners: {', '.join(owners)}")

            categories = set(t.category for t in transactions if t.category)
            logger.info(f"     Categories: {len(categories)} unique")

        all_transactions.extend(transactions)

    # Final summary
    logger.info("\n" + "="*70)
    logger.info("FINAL SUMMARY")
    logger.info("="*70)
    logger.info(f"Total transactions normalized: {len(all_transactions)}")

    if all_transactions:
        total_eur = sum(t.amount_eur for t in all_transactions if t.amount_eur)
        logger.info(f"Total value in EUR: {total_eur:.2f}")

        # Group by institution
        by_institution = {}
        for txn in all_transactions:
            if txn.institution not in by_institution:
                by_institution[txn.institution] = []
            by_institution[txn.institution].append(txn)

        logger.info(f"\nBreakdown by institution:")
        for inst, txns in by_institution.items():
            inst_total = sum(t.amount_eur for t in txns if t.amount_eur)
            logger.info(f"  {inst}: {len(txns)} transactions, {inst_total:.2f} EUR")

    logger.info("\n" + "="*70)
    logger.info("TEST COMPLETE")
    logger.info("="*70)
    logger.info("\nNext steps:")
    logger.info("  1. Implement writer to save to Google Sheets")
    logger.info("  2. Implement file scanner")
    logger.info("  3. Create main.py orchestration")


if __name__ == "__main__":
    main()
