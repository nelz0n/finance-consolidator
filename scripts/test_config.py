"""Test institution configuration with a sample file."""

import sys
import argparse
from pathlib import Path
import yaml

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.parser import FileParser
from src.core.normalizer import DataNormalizer
from src.utils import CurrencyConverter, setup_logger


def load_institution_config(institution_name: str) -> dict:
    """Load institution configuration by name."""
    config_dir = Path("config/institutions")

    # Try exact match
    config_file = config_dir / f"{institution_name.lower().replace(' ', '_')}.yaml"

    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    # Try searching all files
    for yaml_file in config_dir.glob("*.yaml"):
        with open(yaml_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if config.get('institution', {}).get('name', '').lower() == institution_name.lower():
                return config

    return None


def test_config(institution_name: str, file_path: str, show_all: bool = False):
    """
    Test institution configuration with a sample file.

    Args:
        institution_name: Name of the institution
        file_path: Path to sample file
        show_all: Show all transactions (not just first 5)
    """
    logger = setup_logger(level='INFO', console=True)

    logger.info("="*70)
    logger.info(f"TESTING CONFIGURATION: {institution_name}")
    logger.info("="*70)

    # Load config
    logger.info(f"\n1. Loading configuration for '{institution_name}'...")
    config = load_institution_config(institution_name)

    if not config:
        logger.error(f"❌ Configuration not found for '{institution_name}'")
        logger.error("\nAvailable institutions:")

        config_dir = Path("config/institutions")
        for yaml_file in config_dir.glob("*.yaml"):
            with open(yaml_file, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f)
                name = cfg.get('institution', {}).get('name', yaml_file.stem)
                logger.info(f"  - {name}")

        return False

    logger.info(f"✅ Loaded configuration")
    logger.info(f"   Institution: {config['institution']['name']}")
    logger.info(f"   Type: {config['institution']['type']}")

    # Check file exists
    logger.info(f"\n2. Checking file: {file_path}")
    if not Path(file_path).exists():
        logger.error(f"❌ File not found: {file_path}")
        return False

    logger.info(f"✅ File exists")
    file_size = Path(file_path).stat().st_size
    logger.info(f"   Size: {file_size:,} bytes")

    # Parse file
    logger.info(f"\n3. Parsing file...")
    parser = FileParser(config)

    try:
        raw_transactions = parser.parse_file(file_path)
        logger.info(f"✅ Successfully parsed {len(raw_transactions)} raw transactions")
    except Exception as e:
        logger.error(f"❌ Parsing failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

    if not raw_transactions:
        logger.warning("⚠️  No transactions found in file")
        return False

    # Show sample raw data
    logger.info(f"\n4. Sample raw data (first transaction):")
    sample = raw_transactions[0]
    for key, value in list(sample.items())[:10]:
        display_value = str(value)[:50]
        if len(str(value)) > 50:
            display_value += "..."
        logger.info(f"   {key}: {display_value}")

    if len(sample) > 10:
        logger.info(f"   ... and {len(sample) - 10} more fields")

    # Test normalization
    logger.info(f"\n5. Testing normalization...")

    # Load currency converter
    with open('config/settings.yaml', 'r') as f:
        settings = yaml.safe_load(f)

    converter = CurrencyConverter(
        rates=settings['currency']['rates'],
        base_currency=settings['currency']['base_currency']
    )

    normalizer = DataNormalizer(converter, config)

    try:
        transactions = normalizer.normalize_transactions(
            raw_transactions,
            Path(file_path).name
        )
        logger.info(f"✅ Successfully normalized {len(transactions)} transactions")
    except Exception as e:
        logger.error(f"❌ Normalization failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

    if not transactions:
        logger.warning("⚠️  No transactions after normalization")
        return False

    # Show normalized samples
    num_to_show = len(transactions) if show_all else min(5, len(transactions))
    logger.info(f"\n6. Normalized transactions (showing {num_to_show}):")

    for i, txn in enumerate(transactions[:num_to_show], 1):
        logger.info(f"\n   Transaction {i}:")
        logger.info(f"     ID: {txn.transaction_id}")
        logger.info(f"     Date: {txn.date.strftime('%Y-%m-%d')}")
        logger.info(f"     Description: {txn.description[:50]}...")
        logger.info(f"     Amount: {txn.amount} {txn.currency}")
        logger.info(f"     Amount CZK: {txn.amount_czk}")
        logger.info(f"     Category Tier1: {txn.category_tier1}")
        logger.info(f"     Owner: {txn.owner}")
        logger.info(f"     Institution: {txn.institution}")

    if len(transactions) > num_to_show:
        logger.info(f"\n   ... and {len(transactions) - num_to_show} more transactions")

    # Statistics
    logger.info(f"\n7. Statistics:")
    logger.info(f"   Total transactions: {len(transactions)}")

    total_amount = sum(t.amount for t in transactions)
    logger.info(f"   Total amount: {total_amount}")

    total_czk = sum(t.amount_czk for t in transactions if t.amount_czk)
    logger.info(f"   Total CZK: {total_czk:.2f}")

    # Unique values
    owners = set(t.owner for t in transactions)
    logger.info(f"   Owners: {', '.join(owners)}")

    categories = set(t.category_tier1 for t in transactions if t.category_tier1)
    logger.info(f"   Categories: {len(categories)} unique")

    currencies = set(t.currency for t in transactions)
    logger.info(f"   Currencies: {', '.join(currencies)}")

    # Date range
    dates = [t.date for t in transactions]
    logger.info(f"   Date range: {min(dates).strftime('%Y-%m-%d')} to {max(dates).strftime('%Y-%m-%d')}")

    # Configuration validation
    logger.info(f"\n8. Configuration validation:")

    warnings = []

    # Check required fields
    required_fields = ['date', 'amount', 'currency']
    for field in required_fields:
        missing = [t for t in transactions if not getattr(t, field, None)]
        if missing:
            warnings.append(f"⚠️  {len(missing)} transactions missing '{field}'")

    # Check owner detection
    unknown_owners = [t for t in transactions if t.owner == 'Unknown']
    if unknown_owners:
        warnings.append(f"⚠️  {len(unknown_owners)} transactions have 'Unknown' owner")

    # Check category mapping
    uncategorized = [t for t in transactions if not t.category or t.category == 'Uncategorized']
    if uncategorized:
        warnings.append(f"⚠️  {len(uncategorized)} transactions are uncategorized")

    if warnings:
        for warning in warnings:
            logger.warning(f"   {warning}")
    else:
        logger.info(f"   ✅ No issues found")

    # Summary
    logger.info(f"\n" + "="*70)
    logger.info("TEST SUMMARY")
    logger.info("="*70)
    logger.info(f"✅ Configuration: Valid")
    logger.info(f"✅ Parsing: {len(raw_transactions)} raw transactions")
    logger.info(f"✅ Normalization: {len(transactions)} transactions")

    if warnings:
        logger.info(f"⚠️  Warnings: {len(warnings)}")
    else:
        logger.info(f"✅ No warnings")

    logger.info("="*70)

    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Test institution configuration with a sample file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test_config.py --institution "ČSOB" --file data/temp/csob_export.csv
  python scripts/test_config.py --institution Partners --file data/temp/vypis.xlsx --all
  python scripts/test_config.py -i Wise -f data/temp/transaction-history.csv
        """
    )

    parser.add_argument(
        '--institution', '-i',
        required=True,
        help='Institution name (e.g., "ČSOB", "Partners Bank", "Wise")'
    )

    parser.add_argument(
        '--file', '-f',
        required=True,
        help='Path to sample file to test'
    )

    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='Show all transactions (not just first 5)'
    )

    args = parser.parse_args()

    success = test_config(args.institution, args.file, args.all)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
