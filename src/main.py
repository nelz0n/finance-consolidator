"""
Main entry point for Finance Consolidator

Orchestrates the entire pipeline:
1. Scan Google Drive for files
2. Parse files based on institution configs
3. Normalize transactions
4. Write to Google Sheets master file
"""

import argparse
import sys
import yaml
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, date
import tempfile

from src.utils.logger import setup_logger
from src.utils.currency import CurrencyConverter
from src.utils.date_parser import get_date_range
from src.utils.categorizer import get_categorizer
from src.connectors.google_drive import GoogleDriveConnector
from src.connectors.google_sheets import GoogleSheetsConnector
from src.core.file_scanner import FileScanner
from src.core.parser import FileParser
from src.core.normalizer import DataNormalizer
from src.core.writer import SheetsWriter
from src.models.transaction import Transaction


def load_config(config_path: str = "config/settings.yaml") -> Dict[str, Any]:
    """
    Load main configuration file.

    Args:
        config_path: Path to settings.yaml

    Returns:
        Configuration dictionary
    """
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Finance Consolidator - Aggregate financial data from multiple institutions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all new files
  python -m src.main

  # Dry run (see what would be processed)
  python -m src.main --dry-run

  # Process specific institution
  python -m src.main --institution "ČSOB"

  # Process date range
  python -m src.main --from-date 2024-10-01 --to-date 2024-10-31

  # Verbose logging
  python -m src.main --verbose

  # Force reprocess (overwrite existing data)
  python -m src.main --force
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without writing to Google Sheets (preview mode)'
    )

    parser.add_argument(
        '--institution',
        type=str,
        help='Process only files from specific institution (e.g., "ČSOB", "Wise", "Partners Bank")'
    )

    parser.add_argument(
        '--from-date',
        type=str,
        help='Process transactions from this date (format: YYYY-MM-DD)'
    )

    parser.add_argument(
        '--to-date',
        type=str,
        help='Process transactions until this date (format: YYYY-MM-DD)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging (DEBUG level)'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Force reprocess - overwrite existing data instead of appending'
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config/settings.yaml',
        help='Path to configuration file (default: config/settings.yaml)'
    )

    parser.add_argument(
        '--no-duplicate-check',
        action='store_true',
        help='Skip duplicate detection (faster but may create duplicates)'
    )

    parser.add_argument(
        '--reload-rules',
        action='store_true',
        help='Force reload categorization rules from Google Sheets (bypass cache)'
    )

    return parser.parse_args()


def filter_duplicates(transactions: List[Transaction],
                      existing_ids: set,
                      logger) -> List[Transaction]:
    """
    Filter out transactions that already exist in the sheet.

    Args:
        transactions: List of transactions to check
        existing_ids: Set of existing transaction IDs
        logger: Logger instance

    Returns:
        List of new transactions (not duplicates)
    """
    if not existing_ids:
        logger.info("No existing transactions found - all transactions are new")
        return transactions

    new_transactions = []
    duplicates = 0

    for txn in transactions:
        if txn.transaction_id not in existing_ids:
            new_transactions.append(txn)
        else:
            duplicates += 1

    logger.info(f"Duplicate detection: {duplicates} duplicates, {len(new_transactions)} new transactions")

    return new_transactions


def main():
    """Main execution function."""
    # Parse arguments
    args = parse_arguments()

    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

    # Setup logger
    log_level = 'DEBUG' if args.verbose else config.get('logging', {}).get('level', 'INFO')
    log_file = config.get('logging', {}).get('file', 'data/logs/finance_consolidator.log')
    console = config.get('logging', {}).get('console', True)

    logger = setup_logger(level=log_level, log_file=log_file, console=console)

    logger.info("=" * 80)
    logger.info("Finance Consolidator - Starting")
    logger.info("=" * 80)

    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No data will be written to Google Sheets")

    if args.force:
        logger.warning("⚠️  FORCE MODE - Will overwrite existing data")

    # Display configuration
    logger.info(f"Configuration file: {args.config}")
    logger.info(f"Institution filter: {args.institution or 'All'}")
    logger.info(f"Date range: {args.from_date or 'Start'} to {args.to_date or 'End'}")

    try:
        # Initialize Google Drive connector
        logger.info("Initializing Google Drive connector...")
        drive = GoogleDriveConnector(
            credentials_path=config['google_drive']['credentials_path'],
            token_path=config['google_drive']['token_path']
        )
        if not drive.authenticate():
            logger.error("Failed to authenticate with Google Drive")
            sys.exit(1)
        logger.info("✓ Google Drive connected")

        # Initialize Google Sheets connector
        logger.info("Initializing Google Sheets connector...")
        sheets = GoogleSheetsConnector(
            credentials_path=config['google_drive']['credentials_path'],
            token_path=config['google_drive']['token_path']
        )
        if not sheets.authenticate():
            logger.error("Failed to authenticate with Google Sheets")
            sys.exit(1)
        logger.info("✓ Google Sheets connected")

        # Initialize currency converter
        logger.info("Initializing currency converter...")
        converter = CurrencyConverter(
            rates=config['currency']['rates'],
            base_currency=config['currency']['base_currency']
        )
        logger.info(f"✓ Currency converter ready (base: {config['currency']['base_currency']})")

        # Initialize categorizer
        logger.info("Initializing categorizer...")
        categorizer = get_categorizer(
            "config/categorization.yaml",
            "config/settings.yaml",
            reload_rules=args.reload_rules
        )
        logger.info("✓ Categorizer ready")

        # Initialize file scanner
        logger.info("Initializing file scanner...")
        institutions_dir = config['institutions']['config_dir']
        scanner = FileScanner(drive, institutions_dir)

        available_institutions = scanner.list_institutions()
        logger.info(f"✓ Loaded {len(available_institutions)} institution configs: {', '.join(available_institutions)}")

        # Scan for files
        logger.info("\n" + "=" * 80)
        logger.info("Scanning Google Drive for files...")
        logger.info("=" * 80)

        folder_id = config['google_drive']['input_folder_id']
        enabled_institutions = config['institutions'].get('enabled', [])

        # If --institution specified, override enabled list
        if args.institution:
            if args.institution not in available_institutions:
                logger.error(f"Institution '{args.institution}' not found. Available: {', '.join(available_institutions)}")
                sys.exit(1)
            enabled_institutions = [args.institution]

        # If enabled list is empty, process all
        if not enabled_institutions:
            enabled_institutions = None  # Process all

        matched_files = scanner.scan_files(folder_id, enabled_institutions)

        if not matched_files:
            logger.warning("No files found to process")
            logger.info("=" * 80)
            return

        # Process files
        logger.info("\n" + "=" * 80)
        logger.info(f"Processing {len(matched_files)} files...")
        logger.info("=" * 80)

        all_transactions = []
        processed_files = 0
        failed_files = 0

        for file_info in matched_files:
            filename = file_info['filename']
            institution = file_info['institution']
            file_id = file_info['file_id']

            logger.info(f"\n📄 Processing: {filename} ({institution})")

            try:
                # Download file to temporary directory
                with tempfile.TemporaryDirectory() as temp_dir:
                    local_path = Path(temp_dir) / filename
                    logger.debug(f"Downloading to: {local_path}")

                    # Download with retry logic
                    download_success = drive.download_file(file_id, str(local_path))
                    if not download_success:
                        logger.error(f"Failed to download {filename} after retries")
                        failed_files += 1
                        continue

                    logger.debug(f"✓ Downloaded ({file_info.get('size', 'unknown')} bytes)")

                    # Parse file
                    logger.debug(f"Parsing with {institution} config...")
                    inst_config = file_info['config']
                    parser = FileParser(inst_config)
                    raw_data = parser.parse_file(str(local_path))
                    logger.info(f"✓ Parsed {len(raw_data)} rows")

                    # Normalize data
                    logger.debug("Normalizing transactions...")
                    normalizer = DataNormalizer(converter, inst_config)

                    file_transactions = []
                    for raw_txn in raw_data:
                        txn = normalizer.normalize_transaction(raw_txn, filename)
                        if txn:
                            # Apply categorization
                            txn_dict = txn.to_dict()
                            tier1, tier2, tier3, owner, is_internal, cat_source, ai_conf = categorizer.categorize(txn_dict)

                            # Update transaction with category info
                            txn.category_tier1 = tier1
                            txn.category_tier2 = tier2
                            txn.category_tier3 = tier3
                            txn.is_internal_transfer = is_internal
                            txn.categorization_source = cat_source
                            txn.ai_confidence = ai_conf

                            # Update owner (from rules or owner_mapping)
                            if owner:
                                txn.owner = owner

                            file_transactions.append(txn)

                    logger.info(f"✓ Normalized {len(file_transactions)} transactions")

                    all_transactions.extend(file_transactions)
                    processed_files += 1

                    # Small delay between files to avoid connection issues
                    if processed_files < len(matched_files):
                        time.sleep(0.5)  # 500ms delay

            except Exception as e:
                logger.error(f"✗ Failed to process {filename}: {str(e)}")
                if args.verbose:
                    import traceback
                    logger.debug(traceback.format_exc())
                failed_files += 1
                continue

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info(f"Processing Summary:")
        logger.info(f"  Files processed: {processed_files}/{len(matched_files)}")
        logger.info(f"  Files failed: {failed_files}")
        logger.info(f"  Total transactions: {len(all_transactions)}")

        # Count internal transfers
        internal_count = sum(1 for txn in all_transactions if txn.is_internal_transfer)
        logger.info(f"  Internal transfers: {internal_count}")

        logger.info("=" * 80)

        if not all_transactions:
            logger.warning("No transactions to write")
            return

        # Filter by date range
        if args.from_date or args.to_date:
            logger.info("\n📅 Filtering by date range...")
            original_count = len(all_transactions)

            start_date, end_date = get_date_range(args.from_date, args.to_date)

            if start_date:
                all_transactions = [t for t in all_transactions if t.date >= start_date]
                logger.info(f"  From date: {start_date}")

            if end_date:
                all_transactions = [t for t in all_transactions if t.date <= end_date]
                logger.info(f"  To date: {end_date}")

            filtered_count = len(all_transactions)
            logger.info(f"  Filtered: {original_count} → {filtered_count} transactions")

        # Duplicate detection
        if not args.no_duplicate_check and not args.force and not args.dry_run:
            logger.info("\n🔍 Checking for duplicates...")
            writer = SheetsWriter(sheets, config['google_sheets']['master_sheet_id'])
            transactions_tab = config['google_sheets']['transactions_tab']

            existing_ids = writer.get_existing_transaction_ids(transactions_tab)
            all_transactions = filter_duplicates(all_transactions, existing_ids, logger)

            if not all_transactions:
                logger.info("All transactions are duplicates - nothing to write")
                return

        # Dry run - just display summary
        if args.dry_run:
            logger.info("\n" + "=" * 80)
            logger.info("DRY RUN - Preview of transactions to be written:")
            logger.info("=" * 80)

            # Group by institution
            by_institution = {}
            for txn in all_transactions:
                inst = txn.institution
                by_institution.setdefault(inst, []).append(txn)

            for inst, txns in by_institution.items():
                logger.info(f"\n{inst}: {len(txns)} transactions")

                # Show first 5 transactions
                for txn in txns[:5]:
                    logger.info(f"  {txn.date} | {txn.amount:>10.2f} {txn.currency} | {txn.description[:50]}")

                if len(txns) > 5:
                    logger.info(f"  ... and {len(txns) - 5} more")

            logger.info("\n" + "=" * 80)
            logger.info("DRY RUN COMPLETE - No data written")
            logger.info("=" * 80)
            return

        # Write to Google Sheets
        logger.info("\n" + "=" * 80)
        logger.info("Writing to Google Sheets...")
        logger.info("=" * 80)

        writer = SheetsWriter(sheets, config['google_sheets']['master_sheet_id'])
        transactions_tab = config['google_sheets']['transactions_tab']

        write_mode = 'overwrite' if args.force else 'append'
        logger.info(f"Mode: {write_mode.upper()}")

        success = writer.write_transactions(
            all_transactions,
            transactions_tab,
            mode=write_mode
        )

        if success:
            logger.info("\n" + "=" * 80)
            logger.info("✅ SUCCESS - Data written to Google Sheets")
            logger.info(f"   Spreadsheet: {config['google_sheets']['master_sheet_id']}")
            logger.info(f"   Tab: {transactions_tab}")
            logger.info(f"   Transactions: {len(all_transactions)}")
            logger.info("=" * 80)
        else:
            logger.error("\n" + "=" * 80)
            logger.error("❌ FAILED - Error writing to Google Sheets")
            logger.error("=" * 80)
            sys.exit(1)

    except KeyboardInterrupt:
        logger.warning("\n\nInterrupted by user")
        sys.exit(130)

    except Exception as e:
        logger.error(f"\n❌ Fatal error: {str(e)}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
