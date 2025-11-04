"""Google Sheets connector for reading and writing data."""

import os
from typing import List, Dict, Optional, Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.connectors.auth import get_credentials
from src.utils.logger import get_logger

logger = get_logger()


class GoogleSheetsConnector:
    """Connector for Google Sheets API operations."""

    def __init__(self, credentials_path: str, token_path: str):
        """
        Initialize Google Sheets connector.

        Args:
            credentials_path: Path to Google API credentials JSON file
            token_path: Path to store/load authentication token
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.creds = None

        logger.info("Initializing Google Sheets connector")

    def authenticate(self) -> bool:
        """
        Authenticate with Google Sheets API using OAuth 2.0 flow.

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Get credentials using shared auth module
            self.creds = get_credentials(self.credentials_path, self.token_path)

            # Build the Sheets service
            self.service = build('sheets', 'v4', credentials=self.creds)
            logger.info("Successfully authenticated with Google Sheets API")
            return True

        except FileNotFoundError as e:
            logger.error(str(e))
            return False
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False

    def read_sheet(
        self,
        spreadsheet_id: str,
        range_name: str
    ) -> Optional[List[List[Any]]]:
        """
        Read data from a Google Sheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The A1 notation range (e.g., "Sheet1!A1:D10" or "Transactions")

        Returns:
            List of lists representing rows, or None if error
        """
        if not self.service:
            logger.error("Not authenticated. Call authenticate() first.")
            return None

        try:
            logger.info(f"Reading sheet: {spreadsheet_id} range: {range_name}")

            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()

            values = result.get('values', [])

            if not values:
                logger.warning(f"No data found in range {range_name}")
                return []

            logger.info(f"Read {len(values)} rows from sheet")
            return values

        except HttpError as e:
            logger.error(f"HTTP error reading sheet: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error reading sheet: {str(e)}")
            return None

    def write_sheet(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: List[List[Any]],
        value_input_option: str = "RAW"
    ) -> bool:
        """
        Write data to a Google Sheet (overwrites existing data).

        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The A1 notation range (e.g., "Sheet1!A1")
            values: List of lists representing rows to write
            value_input_option: How input should be interpreted ("RAW" or "USER_ENTERED")

        Returns:
            True if write successful, False otherwise
        """
        if not self.service:
            logger.error("Not authenticated. Call authenticate() first.")
            return False

        try:
            logger.info(f"Writing {len(values)} rows to {spreadsheet_id} range: {range_name}")

            body = {
                'values': values
            }

            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                body=body
            ).execute()

            updated_cells = result.get('updatedCells', 0)
            logger.info(f"Successfully updated {updated_cells} cells")
            return True

        except HttpError as e:
            logger.error(f"HTTP error writing sheet: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error writing sheet: {str(e)}")
            return False

    def append_sheet(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: List[List[Any]],
        value_input_option: str = "RAW"
    ) -> bool:
        """
        Append data to the end of a Google Sheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The A1 notation range (e.g., "Sheet1!A1" or "Transactions")
            values: List of lists representing rows to append
            value_input_option: How input should be interpreted ("RAW" or "USER_ENTERED")

        Returns:
            True if append successful, False otherwise
        """
        if not self.service:
            logger.error("Not authenticated. Call authenticate() first.")
            return False

        try:
            logger.info(f"Appending {len(values)} rows to {spreadsheet_id} range: {range_name}")

            body = {
                'values': values
            }

            result = self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()

            updated_cells = result.get('updates', {}).get('updatedCells', 0)
            logger.info(f"Successfully appended {len(values)} rows ({updated_cells} cells)")
            return True

        except HttpError as e:
            logger.error(f"HTTP error appending to sheet: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error appending to sheet: {str(e)}")
            return False

    def create_tab(self, spreadsheet_id: str, tab_name: str) -> bool:
        """
        Create a new tab in a spreadsheet if it doesn't exist.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            tab_name: Name of the tab to create

        Returns:
            True if tab created or already exists, False otherwise
        """
        if not self.service:
            logger.error("Not authenticated. Call authenticate() first.")
            return False

        try:
            # Check if tab already exists
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()

            sheets = spreadsheet.get('sheets', [])
            for sheet in sheets:
                if sheet['properties']['title'] == tab_name:
                    logger.info(f"Tab '{tab_name}' already exists")
                    return True

            # Create new tab
            logger.info(f"Creating new tab: {tab_name}")

            requests = [{
                'addSheet': {
                    'properties': {
                        'title': tab_name
                    }
                }
            }]

            body = {
                'requests': requests
            }

            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()

            logger.info(f"Successfully created tab '{tab_name}'")
            return True

        except HttpError as e:
            logger.error(f"HTTP error creating tab: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error creating tab: {str(e)}")
            return False

    def clear_sheet(self, spreadsheet_id: str, range_name: str) -> bool:
        """
        Clear data from a range in a Google Sheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The A1 notation range (e.g., "Sheet1!A1:Z1000")

        Returns:
            True if clear successful, False otherwise
        """
        if not self.service:
            logger.error("Not authenticated. Call authenticate() first.")
            return False

        try:
            logger.info(f"Clearing range {range_name} in {spreadsheet_id}")

            self.service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()

            logger.info(f"Successfully cleared range {range_name}")
            return True

        except HttpError as e:
            logger.error(f"HTTP error clearing sheet: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error clearing sheet: {str(e)}")
            return False

    def get_sheet_names(self, spreadsheet_id: str) -> Optional[List[str]]:
        """
        Get list of all sheet/tab names in a spreadsheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet

        Returns:
            List of sheet names, or None if error
        """
        if not self.service:
            logger.error("Not authenticated. Call authenticate() first.")
            return None

        try:
            logger.debug(f"Getting sheet names for {spreadsheet_id}")

            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()

            sheets = spreadsheet.get('sheets', [])
            sheet_names = [sheet['properties']['title'] for sheet in sheets]

            logger.debug(f"Found {len(sheet_names)} sheets: {', '.join(sheet_names)}")
            return sheet_names

        except HttpError as e:
            logger.error(f"HTTP error getting sheet names: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error getting sheet names: {str(e)}")
            return None

    def batch_update(
        self,
        spreadsheet_id: str,
        data: List[Dict[str, Any]]
    ) -> bool:
        """
        Update multiple ranges in a single batch request.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            data: List of dictionaries with 'range' and 'values' keys

        Returns:
            True if batch update successful, False otherwise

        Example:
            data = [
                {'range': 'Sheet1!A1:B2', 'values': [[1, 2], [3, 4]]},
                {'range': 'Sheet2!A1:C1', 'values': [['a', 'b', 'c']]}
            ]
        """
        if not self.service:
            logger.error("Not authenticated. Call authenticate() first.")
            return False

        try:
            logger.info(f"Batch updating {len(data)} ranges in {spreadsheet_id}")

            body = {
                'valueInputOption': 'RAW',
                'data': data
            }

            result = self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()

            total_updated = result.get('totalUpdatedCells', 0)
            logger.info(f"Successfully updated {total_updated} cells across {len(data)} ranges")
            return True

        except HttpError as e:
            logger.error(f"HTTP error in batch update: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error in batch update: {str(e)}")
            return False

    def format_cells(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
        start_col: int,
        end_col: int,
        format_options: Dict[str, Any]
    ) -> bool:
        """
        Apply formatting to a range of cells.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            sheet_id: The ID of the sheet (not the name)
            start_row: Starting row index (0-based)
            end_row: Ending row index (exclusive)
            start_col: Starting column index (0-based)
            end_col: Ending column index (exclusive)
            format_options: Dictionary with formatting options

        Returns:
            True if formatting successful, False otherwise

        Example format_options:
            {
                'backgroundColor': {'red': 1.0, 'green': 1.0, 'blue': 0.0},
                'textFormat': {'bold': True}
            }
        """
        if not self.service:
            logger.error("Not authenticated. Call authenticate() first.")
            return False

        try:
            logger.debug(f"Applying formatting to cells")

            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': start_row,
                        'endRowIndex': end_row,
                        'startColumnIndex': start_col,
                        'endColumnIndex': end_col
                    },
                    'cell': {
                        'userEnteredFormat': format_options
                    },
                    'fields': 'userEnteredFormat'
                }
            }]

            body = {
                'requests': requests
            }

            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()

            logger.info("Successfully applied formatting")
            return True

        except HttpError as e:
            logger.error(f"HTTP error formatting cells: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error formatting cells: {str(e)}")
            return False
