"""Writer to save data to Google Sheets."""

from typing import List, Optional
from src.models.transaction import Transaction
from src.connectors.google_sheets import GoogleSheetsConnector
from src.utils.logger import get_logger

logger = get_logger()


class SheetsWriter:
    """Write transactions to Google Sheets."""

    def __init__(self, sheets_connector: GoogleSheetsConnector, spreadsheet_id: str):
        """
        Initialize writer.

        Args:
            sheets_connector: GoogleSheetsConnector instance
            spreadsheet_id: Google Sheets spreadsheet ID
        """
        self.sheets = sheets_connector
        self.spreadsheet_id = spreadsheet_id

        logger.info(f"Initialized SheetsWriter for spreadsheet {spreadsheet_id}")

    def write_transactions(
        self,
        transactions: List[Transaction],
        tab_name: str = "Transactions",
        mode: str = "append"
    ) -> bool:
        """
        Write transactions to Google Sheets.

        Args:
            transactions: List of Transaction objects
            tab_name: Name of the sheet tab
            mode: "append" to add to existing data, "overwrite" to replace all data

        Returns:
            True if successful, False otherwise
        """
        if not transactions:
            logger.warning("No transactions to write")
            return True

        logger.info(f"Writing {len(transactions)} transactions to {tab_name} (mode: {mode})")

        try:
            # Ensure tab exists
            if not self.sheets.create_tab(self.spreadsheet_id, tab_name):
                logger.error(f"Failed to create/verify tab: {tab_name}")
                return False

            # Convert transactions to rows
            headers = Transaction.get_header()
            rows = []

            # Define numeric fields that should remain as numbers
            numeric_fields = {'amount', 'amount_czk', 'exchange_rate'}

            for txn in transactions:
                # Get dict and convert to list in header order
                txn_dict = txn.to_dict()
                row = []
                for field in headers:
                    value = txn_dict.get(field, '')
                    # Keep numeric fields as numbers (float), convert rest to string
                    if field in numeric_fields and value not in (None, '', 'None'):
                        row.append(float(value))
                    else:
                        row.append(str(value) if value not in (None, 'None') else '')
                rows.append(row)

            logger.debug(f"Converted {len(rows)} transactions to rows")

            # Write based on mode
            if mode == "overwrite":
                # Clear existing data
                logger.info("Clearing existing data...")
                self.sheets.clear_sheet(self.spreadsheet_id, f"{tab_name}!A:Z")

                # Write headers and data
                all_data = [headers] + rows
                success = self.sheets.write_sheet(
                    self.spreadsheet_id,
                    f"{tab_name}!A1",
                    all_data
                )

            elif mode == "append":
                # Check if we need to add headers
                existing_data = self.sheets.read_sheet(
                    self.spreadsheet_id,
                    f"{tab_name}!A1:Z1"
                )

                # If sheet is empty OR first row doesn't match expected headers, add/fix headers
                if not existing_data or (existing_data and existing_data[0] != headers):
                    if existing_data:
                        logger.warning("Header row missing or incorrect - adding proper headers")
                    else:
                        logger.info("Adding headers to empty sheet")

                    self.sheets.write_sheet(
                        self.spreadsheet_id,
                        f"{tab_name}!A1",
                        [headers]
                    )

                # Append data
                success = self.sheets.append_sheet(
                    self.spreadsheet_id,
                    f"{tab_name}!A1",
                    rows
                )

            else:
                logger.error(f"Invalid mode: {mode}")
                return False

            if success:
                logger.info(f"✅ Successfully wrote {len(transactions)} transactions")
                return True
            else:
                logger.error("Failed to write transactions")
                return False

        except Exception as e:
            logger.error(f"Error writing transactions: {str(e)}")
            return False

    def write_batch(
        self,
        transactions: Optional[List[Transaction]] = None,
        transactions_tab: str = "Transactions",
        mode: str = "append"
    ) -> bool:
        """
        Write transactions in batch.

        Args:
            transactions: List of Transaction objects
            transactions_tab: Name of transactions tab
            mode: "append" or "overwrite"

        Returns:
            True if all writes successful, False otherwise
        """
        logger.info("Starting batch write operation")

        success = True

        if transactions:
            if not self.write_transactions(transactions, transactions_tab, mode):
                success = False
                logger.error("Failed to write transactions")

        if success:
            logger.info("✅ Batch write completed successfully")
        else:
            logger.error("❌ Batch write had errors")

        return success

    def get_existing_transaction_ids(self, tab_name: str = "Transactions") -> set:
        """
        Get set of existing transaction IDs from sheet.

        Useful for duplicate detection.

        Args:
            tab_name: Name of transactions tab

        Returns:
            Set of transaction IDs
        """
        try:
            # Read transaction ID column (column A)
            data = self.sheets.read_sheet(
                self.spreadsheet_id,
                f"{tab_name}!A:A"
            )

            if not data:
                return set()

            # Skip header, get IDs
            transaction_ids = set()
            for row in data[1:]:  # Skip header
                if row:  # Skip empty rows
                    transaction_ids.add(row[0])

            logger.info(f"Found {len(transaction_ids)} existing transaction IDs")
            return transaction_ids

        except Exception as e:
            logger.error(f"Error reading existing transaction IDs: {str(e)}")
            return set()

    def clear_all_data(
        self,
        transactions_tab: str = "Transactions"
    ) -> bool:
        """
        Clear all data from transactions tab.

        Args:
            transactions_tab: Name of transactions tab

        Returns:
            True if successful
        """
        logger.warning("Clearing all data from sheets")

        try:
            success = self.sheets.clear_sheet(self.spreadsheet_id, f"{transactions_tab}!A:Z")

            if success:
                logger.info("✅ All data cleared")
            else:
                logger.error("❌ Failed to clear data")

            return success

        except Exception as e:
            logger.error(f"Error clearing data: {str(e)}")
            return False
