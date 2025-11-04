"""Test script for Google Sheets connector."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.connectors.google_sheets import GoogleSheetsConnector
from src.utils.logger import setup_logger

def main():
    """Test Google Sheets connection and operations."""

    # Setup logger
    logger = setup_logger(level='INFO', console=True)

    # Paths from config
    credentials_path = "data/credentials/google_credentials.json"
    token_path = "data/credentials/token.pickle"
    spreadsheet_id = "10H6uDqvYs2iBpwBDxH-zEfSrSMAq6J5JbjKVR5NkG_w"  # From settings.yaml

    logger.info("=== Testing Google Sheets Connector ===")

    # Initialize connector
    sheets = GoogleSheetsConnector(credentials_path, token_path)

    # Authenticate
    logger.info("Step 1: Authenticating...")
    if not sheets.authenticate():
        logger.error("Authentication failed!")
        return

    logger.info("✓ Authentication successful")

    # Get sheet names
    logger.info("\nStep 2: Getting sheet names...")
    sheet_names = sheets.get_sheet_names(spreadsheet_id)

    if sheet_names:
        logger.info(f"✓ Found {len(sheet_names)} sheets:")
        for i, name in enumerate(sheet_names, 1):
            logger.info(f"  {i}. {name}")
    else:
        logger.warning("No sheets found or error occurred")

    # Create test tabs if they don't exist
    logger.info("\nStep 3: Creating test tabs...")

    for tab_name in ["Transactions", "Balances"]:
        if sheets.create_tab(spreadsheet_id, tab_name):
            logger.info(f"✓ Tab '{tab_name}' ready")
        else:
            logger.error(f"✗ Failed to create tab '{tab_name}'")

    # Test write operation
    logger.info("\nStep 4: Testing write operation...")

    # Create sample data
    test_data = [
        ["Test Column 1", "Test Column 2", "Test Column 3"],
        ["Value 1", "Value 2", "Value 3"],
        ["Value 4", "Value 5", "Value 6"]
    ]

    if sheets.write_sheet(spreadsheet_id, "Transactions!A1", test_data):
        logger.info("✓ Successfully wrote test data")
    else:
        logger.error("✗ Failed to write test data")

    # Test read operation
    logger.info("\nStep 5: Testing read operation...")

    read_data = sheets.read_sheet(spreadsheet_id, "Transactions!A1:C3")

    if read_data:
        logger.info(f"✓ Successfully read {len(read_data)} rows:")
        for row in read_data:
            logger.info(f"  {row}")
    else:
        logger.error("✗ Failed to read data")

    # Test append operation
    logger.info("\nStep 6: Testing append operation...")

    append_data = [
        ["Appended 1", "Appended 2", "Appended 3"]
    ]

    if sheets.append_sheet(spreadsheet_id, "Transactions!A1", append_data):
        logger.info("✓ Successfully appended data")
    else:
        logger.error("✗ Failed to append data")

    # Read again to verify append
    logger.info("\nStep 7: Verifying append...")

    read_data = sheets.read_sheet(spreadsheet_id, "Transactions!A1:C10")

    if read_data:
        logger.info(f"✓ Now have {len(read_data)} rows total")
    else:
        logger.error("✗ Failed to verify")

    # Test clear operation
    logger.info("\nStep 8: Testing clear operation...")

    if sheets.clear_sheet(spreadsheet_id, "Transactions!A1:Z100"):
        logger.info("✓ Successfully cleared test data")
    else:
        logger.error("✗ Failed to clear data")

    # Test batch update
    logger.info("\nStep 9: Testing batch update...")

    batch_data = [
        {
            'range': 'Transactions!A1:C1',
            'values': [['transaction_id', 'date', 'amount']]
        },
        {
            'range': 'Balances!A1:C1',
            'values': [['balance_id', 'date', 'value']]
        }
    ]

    if sheets.batch_update(spreadsheet_id, batch_data):
        logger.info("✓ Successfully batch updated headers")
    else:
        logger.error("✗ Failed batch update")

    # Verify the batch update
    logger.info("\nStep 10: Verifying batch update...")

    txn_headers = sheets.read_sheet(spreadsheet_id, "Transactions!A1:C1")
    bal_headers = sheets.read_sheet(spreadsheet_id, "Balances!A1:C1")

    if txn_headers and bal_headers:
        logger.info(f"✓ Transactions headers: {txn_headers[0]}")
        logger.info(f"✓ Balances headers: {bal_headers[0]}")
    else:
        logger.error("✗ Failed to verify batch update")

    logger.info("\n=== Test Complete ===")
    logger.info("\nCheck your Google Sheet at:")
    logger.info(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")

if __name__ == "__main__":
    main()
