"""Test script for Google Drive connector."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.connectors.google_drive import GoogleDriveConnector
from src.utils.logger import setup_logger

def main():
    """Test Google Drive connection and file listing."""

    # Setup logger
    logger = setup_logger(level='INFO', console=True)

    # Paths from config
    credentials_path = "data/credentials/google_credentials.json"
    token_path = "data/credentials/token.pickle"
    folder_id = "1CrtDt9JR9pNrE4I9HKxjnVxrb9Eh9E5b"  # From settings.yaml

    logger.info("=== Testing Google Drive Connector ===")

    # Initialize connector
    drive = GoogleDriveConnector(credentials_path, token_path)

    # Authenticate
    logger.info("Step 1: Authenticating...")
    if not drive.authenticate():
        logger.error("Authentication failed!")
        return

    logger.info("✓ Authentication successful")

    # List all files
    logger.info("\nStep 2: Listing all files in folder...")
    files = drive.list_files(folder_id)

    if files:
        logger.info(f"✓ Found {len(files)} files:")
        for i, file in enumerate(files, 1):
            logger.info(f"  {i}. {file['name']}")
            logger.info(f"     ID: {file['id']}")
            logger.info(f"     Modified: {file['modified_time']}")
    else:
        logger.warning("No files found")

    # List ČSOB files
    logger.info("\nStep 3: Listing ČSOB files...")
    csob_files = drive.list_files(folder_id, file_pattern="csob_*.csv")

    if csob_files:
        logger.info(f"✓ Found {len(csob_files)} ČSOB files:")
        for file in csob_files:
            logger.info(f"  - {file['name']}")
    else:
        logger.info("No ČSOB files found")

    # List Partners files
    logger.info("\nStep 4: Listing Partners files...")
    partners_files = drive.list_files(folder_id, file_pattern="vypis_*.xlsx")

    if partners_files:
        logger.info(f"✓ Found {len(partners_files)} Partners files:")
        for file in partners_files:
            logger.info(f"  - {file['name']}")
    else:
        logger.info("No Partners files found")

    # List Wise files
    logger.info("\nStep 5: Listing Wise files...")
    wise_files = drive.list_files(folder_id, file_pattern="transaction-history*.csv")

    if wise_files:
        logger.info(f"✓ Found {len(wise_files)} Wise files:")
        for file in wise_files:
            logger.info(f"  - {file['name']}")
    else:
        logger.info("No Wise files found")

    # Test download (optional - commented out to avoid downloading)
    # if files:
    #     logger.info(f"\nStep 6: Testing download of first file...")
    #     test_file = files[0]
    #     destination = f"data/temp/{test_file['name']}"
    #     if drive.download_file(test_file['id'], destination):
    #         logger.info(f"✓ Successfully downloaded to {destination}")
    #     else:
    #         logger.error("Download failed")

    logger.info("\n=== Test Complete ===")

if __name__ == "__main__":
    main()
