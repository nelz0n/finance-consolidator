"""Test Google Sheets-based categorization."""

import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.categorizer import get_categorizer
from src.utils.logger import setup_logger

logger = setup_logger(level='INFO', console=True)


def test_categorization():
    """Test categorization with Google Sheets rules."""

    logger.info("="*70)
    logger.info("TESTING GOOGLE SHEETS CATEGORIZATION")
    logger.info("="*70)

    # Initialize categorizer
    logger.info("\n1. Initializing categorizer with Google Sheets rules...")
    try:
        categorizer = get_categorizer(
            "config/categorization.yaml",
            "config/settings.yaml",
            reload_rules=True  # Force reload from Sheets
        )
        logger.info("✅ Categorizer initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize categorizer: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

    # Test transactions
    logger.info("\n2. Testing categorization with sample transactions...")

    test_transactions = [
        {
            "description": "ALBERT SUPERMARKET PRAHA",
            "counterparty_name": "ALBERT",
            "counterparty_account": "",
            "amount": Decimal("-150.00"),
            "amount_czk": Decimal("-150.00"),
            "institution": "ČSOB",
            "account": "283337817/0300",
            "variable_symbol": "",
            "date": datetime(2024, 11, 1),
            "owner": "Unknown"
        },
        {
            "description": "TESCO STORE #4251",
            "counterparty_name": "TESCO",
            "counterparty_account": "",
            "amount": Decimal("-89.50"),
            "amount_czk": Decimal("-89.50"),
            "institution": "Partners Bank",
            "account": "1330299329/6363",
            "variable_symbol": "",
            "date": datetime(2024, 11, 2),
            "owner": "Unknown"
        },
        {
            "description": "Shell Fuel Station",
            "counterparty_name": "Shell CZ",
            "counterparty_account": "",
            "amount": Decimal("-1200.00"),
            "amount_czk": Decimal("-1200.00"),
            "institution": "ČSOB",
            "account": "283337817/0300",
            "variable_symbol": "",
            "date": datetime(2024, 11, 3),
            "owner": "Unknown"
        },
        {
            "description": "Netflix Subscription",
            "counterparty_name": "NETFLIX.COM",
            "counterparty_account": "",
            "amount": Decimal("-9.99"),
            "amount_czk": Decimal("-244.76"),
            "institution": "Wise",
            "account": "Wise",
            "variable_symbol": "",
            "date": datetime(2024, 11, 4),
            "owner": "Unknown"
        },
        {
            "description": "Unknown merchant",
            "counterparty_name": "XYZ COMPANY",
            "counterparty_account": "",
            "amount": Decimal("-500.00"),
            "amount_czk": Decimal("-500.00"),
            "institution": "ČSOB",
            "account": "210621040/0300",
            "variable_symbol": "",
            "date": datetime(2024, 11, 5),
            "owner": "Unknown"
        }
    ]

    results = []
    for i, txn in enumerate(test_transactions, 1):
        logger.info(f"\n   Transaction {i}:")
        logger.info(f"     Description: {txn['description']}")
        logger.info(f"     Institution: {txn['institution']}")
        logger.info(f"     Account: {txn['account']}")
        logger.info(f"     Amount: {txn['amount_czk']} CZK")

        try:
            tier1, tier2, tier3, owner, is_internal = categorizer.categorize(txn)

            logger.info(f"     ➜ Category: {tier1} > {tier2} > {tier3}")
            logger.info(f"     ➜ Owner: {owner}")
            logger.info(f"     ➜ Internal: {is_internal}")

            results.append({
                'description': txn['description'],
                'tier1': tier1,
                'tier2': tier2,
                'tier3': tier3,
                'owner': owner,
                'is_internal': is_internal
            })
        except Exception as e:
            logger.error(f"     ❌ Categorization failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            results.append(None)

    # Summary
    logger.info("\n" + "="*70)
    logger.info("TEST SUMMARY")
    logger.info("="*70)

    successful = sum(1 for r in results if r is not None)
    logger.info(f"✅ Successfully categorized: {successful}/{len(test_transactions)} transactions")

    # Count categories
    categorized = sum(1 for r in results if r and r['tier1'] != 'Uncategorized')
    logger.info(f"✅ Categorized (not Unknown): {categorized}/{len(test_transactions)}")

    # Count owners
    owner_counts = {}
    for r in results:
        if r:
            owner = r['owner']
            owner_counts[owner] = owner_counts.get(owner, 0) + 1

    logger.info(f"\n📊 Owner distribution:")
    for owner, count in owner_counts.items():
        logger.info(f"   {owner}: {count} transactions")

    # Check if rules from Sheets were applied
    if categorized > 0:
        logger.info(f"\n✅ Google Sheets rules are working! {categorized} transactions matched rules.")
    else:
        logger.warning(f"\n⚠️  No transactions matched Google Sheets rules. Check the rules in the spreadsheet.")

    logger.info("="*70)

    return True


def main():
    """Main entry point."""
    try:
        success = test_categorization()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
