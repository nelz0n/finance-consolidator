"""Service to read transactions from Google Sheets"""
import yaml
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import date, datetime
from decimal import Decimal

from src.connectors.google_sheets import GoogleSheetsConnector
from src.models.transaction import Transaction


class SheetsTransactionService:
    """Service to read and query transactions from Google Sheets"""

    def __init__(self):
        """Initialize the service with Google Sheets connection"""
        # Load settings
        with open("config/settings.yaml", 'r', encoding='utf-8') as f:
            settings = yaml.safe_load(f)

        self.spreadsheet_id = settings['google_sheets']['master_sheet_id']
        creds_path = settings['google_drive']['credentials_path']
        token_path = settings['google_drive']['token_path']

        # Connect to Google Sheets
        self.sheets = GoogleSheetsConnector(creds_path, token_path)
        if not self.sheets.authenticate():
            raise Exception("Failed to authenticate with Google Sheets")

    def _parse_transaction_row(self, headers: List[str], row: List) -> Optional[Dict]:
        """Parse a row from Google Sheets into a transaction dict"""
        if len(row) < len(headers):
            # Pad row with empty strings
            row = row + [''] * (len(headers) - len(row))

        transaction = {}
        for i, header in enumerate(headers):
            value = row[i] if i < len(row) else ''

            # Clean empty values
            if value in ('', 'None', None):
                value = None

            transaction[header] = value

        # Skip empty rows
        if not transaction.get('date'):
            return None

        return transaction

    def get_all_transactions(
        self,
        skip: int = 0,
        limit: int = 50,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        owner: Optional[str] = None,
        institution: Optional[str] = None,
        category_tier1: Optional[str] = None,
        category_tier2: Optional[str] = None,
        category_tier3: Optional[str] = None,
        is_internal_transfer: Optional[bool] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        search: Optional[str] = None,
        sort_by: str = "date",
        sort_order: str = "desc"
    ) -> Tuple[List[Dict], int]:
        """
        Get transactions from Google Sheets with filtering and pagination

        Returns:
            Tuple of (filtered_transactions, total_count)
        """
        # Read all data from Transactions tab
        data = self.sheets.read_sheet(self.spreadsheet_id, "Transactions!A:Z")

        if not data or len(data) < 2:
            return [], 0

        # Parse headers and rows
        headers = [h.lower().replace(' ', '_') for h in data[0]]
        transactions = []

        for row_idx, row in enumerate(data[1:], start=2):  # Start at 2 because row 1 is header
            txn = self._parse_transaction_row(headers, row)
            if txn:
                txn['_row_number'] = row_idx  # Add row number for updates
                transactions.append(txn)

        # Apply filters
        filtered = self._filter_transactions(
            transactions,
            from_date=from_date,
            to_date=to_date,
            owner=owner,
            institution=institution,
            category_tier1=category_tier1,
            category_tier2=category_tier2,
            category_tier3=category_tier3,
            is_internal_transfer=is_internal_transfer,
            min_amount=min_amount,
            max_amount=max_amount,
            search=search
        )

        # Sort
        filtered = self._sort_transactions(filtered, sort_by, sort_order)

        total = len(filtered)

        # Paginate
        end = skip + limit
        paginated = filtered[skip:end]

        return paginated, total

    def _filter_transactions(
        self,
        transactions: List[Dict],
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        owner: Optional[str] = None,
        institution: Optional[str] = None,
        category_tier1: Optional[str] = None,
        category_tier2: Optional[str] = None,
        category_tier3: Optional[str] = None,
        is_internal_transfer: Optional[bool] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        search: Optional[str] = None
    ) -> List[Dict]:
        """Apply filters to transactions"""
        filtered = transactions

        # Date filters
        if from_date:
            filtered = [t for t in filtered if self._parse_date(t.get('date')) >= from_date]
        if to_date:
            filtered = [t for t in filtered if self._parse_date(t.get('date')) <= to_date]

        # Owner filter
        if owner:
            filtered = [t for t in filtered if t.get('owner', '').lower() == owner.lower()]

        # Institution filter
        if institution:
            filtered = [t for t in filtered if t.get('institution', '').lower() == institution.lower()]

        # Category filters
        if category_tier1:
            filtered = [t for t in filtered if t.get('category_tier1', '').lower() == category_tier1.lower()]
        if category_tier2:
            filtered = [t for t in filtered if t.get('category_tier2', '').lower() == category_tier2.lower()]
        if category_tier3:
            filtered = [t for t in filtered if t.get('category_tier3', '').lower() == category_tier3.lower()]

        # Internal transfer filter
        if is_internal_transfer is not None:
            filtered = [
                t for t in filtered
                if (str(t.get('is_internal_transfer', '')).lower() in ('true', '1', 'yes')) == is_internal_transfer
            ]

        # Amount filters
        if min_amount is not None:
            filtered = [t for t in filtered if self._parse_float(t.get('amount')) >= min_amount]
        if max_amount is not None:
            filtered = [t for t in filtered if self._parse_float(t.get('amount')) <= max_amount]

        # Search filter (search in description, counterparty_name, counterparty_account)
        if search:
            search_lower = search.lower()
            filtered = [
                t for t in filtered
                if (search_lower in str(t.get('description', '')).lower() or
                    search_lower in str(t.get('counterparty_name', '')).lower() or
                    search_lower in str(t.get('counterparty_account', '')).lower())
            ]

        return filtered

    def _sort_transactions(self, transactions: List[Dict], sort_by: str, sort_order: str) -> List[Dict]:
        """Sort transactions"""
        reverse = (sort_order.lower() == 'desc')

        if sort_by == 'date':
            return sorted(transactions, key=lambda t: self._parse_date(t.get('date')) or date.min, reverse=reverse)
        elif sort_by == 'amount':
            return sorted(transactions, key=lambda t: self._parse_float(t.get('amount')), reverse=reverse)
        else:
            return sorted(transactions, key=lambda t: str(t.get(sort_by, '')), reverse=reverse)

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string to date object"""
        if not date_str or date_str in ('', 'None', None):
            return None

        try:
            # Try common formats
            for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%m/%d/%Y']:
                try:
                    return datetime.strptime(str(date_str), fmt).date()
                except ValueError:
                    continue
            return None
        except:
            return None

    def _parse_float(self, value) -> float:
        """Parse float value"""
        if value in ('', 'None', None):
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def get_summary(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        owner: Optional[str] = None
    ) -> Dict:
        """Get summary statistics from transactions"""
        # Get all transactions with filters
        transactions, _ = self.get_all_transactions(
            skip=0,
            limit=999999,  # Get all
            from_date=from_date,
            to_date=to_date,
            owner=owner
        )

        total_income = 0.0
        total_expenses = 0.0
        internal_transfers = 0

        for txn in transactions:
            amount = self._parse_float(txn.get('amount', 0))
            is_internal = str(txn.get('is_internal_transfer', '')).lower() in ('true', '1', 'yes')

            if is_internal:
                internal_transfers += 1
            elif amount > 0:
                total_income += amount
            elif amount < 0:
                total_expenses += abs(amount)

        return {
            'total_transactions': len(transactions),
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_balance': total_income - total_expenses,
            'internal_transfers': internal_transfers
        }

    def get_by_id(self, transaction_id: int) -> Optional[Dict]:
        """Get single transaction by row number (ID)"""
        # Read all data
        data = self.sheets.read_sheet(self.spreadsheet_id, "Transactions!A:Z")

        if not data or len(data) < 2:
            return None

        # transaction_id is 0-based row index (0 = first data row)
        row_index = transaction_id + 1  # +1 for header row

        if row_index >= len(data):
            return None

        headers = [h.lower().replace(' ', '_') for h in data[0]]
        row = data[row_index]

        return self._parse_transaction_row(headers, row)

    def update_transaction(self, transaction_id: int, updates: Dict) -> bool:
        """Update a transaction (by row number)"""
        # Read all data
        data = self.sheets.read_sheet(self.spreadsheet_id, "Transactions!A:Z")

        if not data or len(data) < 2:
            return False

        row_index = transaction_id + 1  # +1 for header row

        if row_index >= len(data):
            return False

        headers = [h.lower().replace(' ', '_') for h in data[0]]
        row = list(data[row_index])

        # Update fields
        for field, value in updates.items():
            if field in headers:
                col_index = headers.index(field)
                if col_index < len(row):
                    row[col_index] = value

        # Write back to sheet
        # Calculate cell range (e.g., A5:Z5 for row 5)
        sheet_row = row_index + 1  # Google Sheets is 1-indexed
        range_name = f"Transactions!A{sheet_row}:Z{sheet_row}"

        return self.sheets.write_sheet(
            self.spreadsheet_id,
            range_name,
            [row],
            overwrite=False
        )
