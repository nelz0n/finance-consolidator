"""Test script for file parser."""

import sys
from pathlib import Path
import yaml
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.connectors import GoogleDriveConnector
from src.core.parser import FileParser
from src.utils.logger import setup_logger


def load_institution_configs(config_dir: str = "config/institutions") -> dict:
    """Load all institution configurations."""
    configs = {}
    config_path = Path(config_dir)

    for yaml_file in config_path.glob("*.yaml"):
        with open(yaml_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            # Use institution name as key
            inst_name = config.get('institution', {}).get('name', yaml_file.stem)
            configs[inst_name] = config
            logger.debug(f"Loaded config for {inst_name}")

    return configs


def main():
    """Test file parser with actual files from Drive."""

    # Setup logger
    global logger
    logger = setup_logger(level='INFO', console=True)

    # Load main config
    with open('config/settings.yaml', 'r') as f:
        settings = yaml.safe_load(f)

    # Load institution configs
    institution_configs = load_institution_configs()

    logger.info("="*70)
    logger.info("FILE PARSER TEST")
    logger.info("="*70)
    logger.info(f"\nLoaded {len(institution_configs)} institution configs:")
    for name in institution_configs.keys():
        logger.info(f"  - {name}")

    # Initialize Drive connector
    drive = GoogleDriveConnector(
        settings['google_drive']['credentials_path'],
        settings['google_drive']['token_path']
    )

    if not drive.authenticate():
        logger.error("Failed to authenticate with Google Drive")
        return

    folder_id = settings['google_drive']['input_folder_id']

    # Create temp directory for downloads
    temp_dir = Path("data/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Test each institution
    institutions_to_test = [
        ('ČSOB', 'csob_*.csv'),
        ('Partners Bank', 'vypis_*.xlsx'),
        ('Wise', 'transaction-history*.csv')
    ]

    for inst_name, pattern in institutions_to_test:
        logger.info("\n" + "="*70)
        logger.info(f"TESTING {inst_name} PARSER")
        logger.info("="*70)

        # Find files
        files = drive.list_files(folder_id, file_pattern=pattern)

        if not files:
            logger.warning(f"No {inst_name} files found with pattern: {pattern}")
            continue

        # Get first file
        test_file = files[0]
        logger.info(f"\nFile: {test_file['name']}")
        logger.info(f"Modified: {test_file['modified_time']}")

        # Download file
        local_path = temp_dir / test_file['name']
        logger.info(f"Downloading to: {local_path}")

        if not drive.download_file(test_file['id'], str(local_path)):
            logger.error(f"Failed to download {test_file['name']}")
            continue

        # Get institution config
        inst_config = institution_configs.get(inst_name)
        if not inst_config:
            logger.error(f"No config found for {inst_name}")
            continue

        # Parse file
        logger.info(f"\nParsing file...")
        parser = FileParser(inst_config)

        try:
            transactions = parser.parse_file(str(local_path))

            logger.info(f"\n✅ Successfully parsed {len(transactions)} transactions")

            # Show first 3 transactions
            if transactions:
                logger.info("\nFirst 3 transactions:")
                for i, txn in enumerate(transactions[:3], 1):
                    logger.info(f"\n  Transaction {i}:")
                    # Show key fields
                    for key in ['date', 'amount', 'currency', 'description', 'institution', 'account']:
                        value = txn.get(key, '')
                        if value:
                            logger.info(f"    {key}: {value}")

            # Show statistics
            logger.info(f"\nStatistics:")
            logger.info(f"  Total transactions: {len(transactions)}")

            # Count fields present
            if transactions:
                all_fields = set()
                for txn in transactions:
                    all_fields.update(txn.keys())
                logger.info(f"  Unique fields: {len(all_fields)}")
                logger.info(f"  Fields: {', '.join(sorted(all_fields)[:10])}...")

        except Exception as e:
            logger.error(f"❌ Failed to parse file: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    logger.info("\n" + "="*70)
    logger.info("PARSER TEST COMPLETE")
    logger.info("="*70)
    logger.info("\nNext steps:")
    logger.info("  1. Review parsed transactions above")
    logger.info("  2. Implement normalizer to convert to Transaction objects")
    logger.info("  3. Test full pipeline")


if __name__ == "__main__":
    main()
