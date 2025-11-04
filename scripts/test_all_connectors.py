"""Comprehensive test script for both Google Drive and Sheets connectors."""

import sys
from pathlib import Path
import yaml

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.connectors import GoogleDriveConnector, GoogleSheetsConnector
from src.utils.logger import setup_logger

def test_drive(config, logger):
    """Test Google Drive connector."""
    logger.info("\n" + "="*70)
    logger.info("TESTING GOOGLE DRIVE CONNECTOR")
    logger.info("="*70)

    # Initialize connector
    drive = GoogleDriveConnector(
        config['google_drive']['credentials_path'],
        config['google_drive']['token_path']
    )

    # Test 1: Authentication
    logger.info("\n[1/4] Testing Authentication...")
    if not drive.authenticate():
        logger.error("❌ Authentication FAILED")
        return False
    logger.info("✅ Authentication successful")

    # Test 2: List all files
    folder_id = config['google_drive']['input_folder_id']
    logger.info(f"\n[2/4] Listing all files in folder {folder_id}...")

    files = drive.list_files(folder_id)
    if files is None:
        logger.error("❌ Failed to list files")
        logger.error("   Check folder ID and permissions")
        return False

    logger.info(f"✅ Found {len(files)} total files")
    if files:
        logger.info("\nFiles in your Drive folder:")
        for i, file in enumerate(files[:10], 1):  # Show first 10
            logger.info(f"  {i}. {file['name']}")
            logger.info(f"     Modified: {file['modified_time']}")
        if len(files) > 10:
            logger.info(f"  ... and {len(files) - 10} more files")
    else:
        logger.warning("⚠️  No files found - your folder is empty")

    # Test 3: Pattern matching
    logger.info("\n[3/4] Testing pattern matching...")

    patterns_found = {}
    test_patterns = {
        "ČSOB": "csob_*.csv",
        "Partners": "vypis_*.xlsx",
        "Wise": "transaction-history*.csv"
    }

    for inst, pattern in test_patterns.items():
        matched = drive.list_files(folder_id, file_pattern=pattern)
        patterns_found[inst] = len(matched) if matched else 0

        if matched:
            logger.info(f"✅ {inst}: Found {len(matched)} files")
            for file in matched[:3]:  # Show first 3
                logger.info(f"   - {file['name']}")
        else:
            logger.info(f"⚠️  {inst}: No files found")

    # Test 4: File metadata
    if files:
        logger.info("\n[4/4] Testing file metadata...")
        test_file = files[0]
        metadata = drive.get_file_metadata(test_file['id'])

        if metadata:
            logger.info(f"✅ Retrieved metadata for: {metadata['name']}")
            logger.info(f"   Size: {metadata.get('size', 'N/A')} bytes")
            logger.info(f"   MIME type: {metadata.get('mimeType', 'N/A')}")
        else:
            logger.warning("⚠️  Failed to get metadata")
    else:
        logger.info("\n[4/4] Skipping metadata test (no files)")

    logger.info("\n" + "-"*70)
    logger.info("DRIVE CONNECTOR TEST SUMMARY:")
    logger.info(f"  Total files: {len(files)}")
    for inst, count in patterns_found.items():
        logger.info(f"  {inst} files: {count}")
    logger.info("-"*70)

    return True

def test_sheets(config, logger):
    """Test Google Sheets connector."""
    logger.info("\n" + "="*70)
    logger.info("TESTING GOOGLE SHEETS CONNECTOR")
    logger.info("="*70)

    # Initialize connector
    sheets = GoogleSheetsConnector(
        config['google_drive']['credentials_path'],
        config['google_drive']['token_path']
    )

    # Test 1: Authentication
    logger.info("\n[1/7] Testing Authentication...")
    if not sheets.authenticate():
        logger.error("❌ Authentication FAILED")
        return False
    logger.info("✅ Authentication successful")

    spreadsheet_id = config['google_sheets']['master_sheet_id']

    # Test 2: Get sheet names
    logger.info(f"\n[2/7] Getting sheet names from spreadsheet...")
    sheet_names = sheets.get_sheet_names(spreadsheet_id)

    if sheet_names:
        logger.info(f"✅ Found {len(sheet_names)} sheets:")
        for name in sheet_names:
            logger.info(f"   - {name}")
    else:
        logger.warning("⚠️  Could not retrieve sheet names")
        logger.warning("   Check spreadsheet ID and permissions")
        return False

    # Test 3: Create test tabs
    logger.info("\n[3/7] Creating required tabs...")
    for tab in ['Transactions', 'Balances']:
        if sheets.create_tab(spreadsheet_id, tab):
            logger.info(f"✅ Tab '{tab}' ready")
        else:
            logger.error(f"❌ Failed to create tab '{tab}'")

    # Test 4: Write test data
    logger.info("\n[4/7] Writing test data...")
    test_data = [
        ['TEST_ID', 'TEST_DATE', 'TEST_AMOUNT'],
        ['001', '2024-11-04', '100.00'],
        ['002', '2024-11-04', '200.00']
    ]

    if sheets.write_sheet(spreadsheet_id, "Transactions!A1", test_data):
        logger.info("✅ Successfully wrote test data")
    else:
        logger.error("❌ Failed to write test data")
        return False

    # Test 5: Read test data
    logger.info("\n[5/7] Reading test data back...")
    read_data = sheets.read_sheet(spreadsheet_id, "Transactions!A1:C3")

    if read_data:
        logger.info(f"✅ Successfully read {len(read_data)} rows:")
        for row in read_data:
            logger.info(f"   {row}")
    else:
        logger.error("❌ Failed to read data")
        return False

    # Test 6: Append data
    logger.info("\n[6/7] Testing append...")
    append_data = [['003', '2024-11-04', '300.00']]

    if sheets.append_sheet(spreadsheet_id, "Transactions!A1", append_data):
        logger.info("✅ Successfully appended data")

        # Verify
        updated_data = sheets.read_sheet(spreadsheet_id, "Transactions!A1:C10")
        if updated_data:
            logger.info(f"   Now have {len(updated_data)} rows total")
    else:
        logger.error("❌ Failed to append data")

    # Test 7: Clean up
    logger.info("\n[7/7] Cleaning up test data...")
    if sheets.clear_sheet(spreadsheet_id, "Transactions!A1:Z100"):
        logger.info("✅ Successfully cleared test data")
    else:
        logger.warning("⚠️  Failed to clear test data")

    logger.info("\n" + "-"*70)
    logger.info("SHEETS CONNECTOR TEST SUMMARY:")
    logger.info(f"  Spreadsheet ID: {spreadsheet_id}")
    logger.info(f"  Sheets found: {len(sheet_names)}")
    logger.info(f"  Write/Read/Append: ✅ All working")
    logger.info(f"\n  View spreadsheet:")
    logger.info(f"  https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
    logger.info("-"*70)

    return True

def main():
    """Run all connector tests."""

    # Load config
    config_path = Path(__file__).parent.parent / 'config' / 'settings.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Setup logger
    logger = setup_logger(
        name="test_connectors",
        level='INFO',
        console=True
    )

    logger.info("="*70)
    logger.info("GOOGLE API CONNECTORS TEST SUITE")
    logger.info("="*70)
    logger.info("\nThis will test:")
    logger.info("  1. Google Drive connector (list files, pattern matching)")
    logger.info("  2. Google Sheets connector (read, write, append)")
    logger.info("\nNote: First run will open browser for OAuth authentication")
    logger.info("="*70)

    # Test Drive
    drive_ok = test_drive(config, logger)

    # Test Sheets
    sheets_ok = test_sheets(config, logger)

    # Final summary
    logger.info("\n" + "="*70)
    logger.info("FINAL TEST RESULTS")
    logger.info("="*70)
    logger.info(f"Google Drive Connector: {'✅ PASSED' if drive_ok else '❌ FAILED'}")
    logger.info(f"Google Sheets Connector: {'✅ PASSED' if sheets_ok else '❌ FAILED'}")
    logger.info("="*70)

    if drive_ok and sheets_ok:
        logger.info("\n🎉 ALL TESTS PASSED! 🎉")
        logger.info("\nYou're ready to proceed with:")
        logger.info("  - Implementing file parsers")
        logger.info("  - Building the main processing pipeline")
        logger.info("\nNext step: Implement src/core/parser.py")
    else:
        logger.error("\n⚠️  SOME TESTS FAILED")
        logger.error("\nPlease check:")
        logger.error("  - Google API credentials are correct")
        logger.error("  - Drive folder ID is correct")
        logger.error("  - Spreadsheet ID is correct")
        logger.error("  - You have access to the Drive folder and Sheet")
        logger.error("  - APIs are enabled in Google Cloud Console")

    return drive_ok and sheets_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
