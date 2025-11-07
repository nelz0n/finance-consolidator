"""Data normalizer to convert raw parsed data to Transaction objects."""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional, List
from collections import defaultdict

from src.models.transaction import Transaction
from src.utils.currency import CurrencyConverter, normalize_currency_code
from src.utils.date_parser import parse_date, parse_czech_date
from src.utils.logger import get_logger

logger = get_logger()


class DataNormalizer:
    """Normalize raw parsed data into Transaction objects."""

    def __init__(self, currency_converter: CurrencyConverter, institution_config: Dict[str, Any]):
        """
        Initialize normalizer.

        Args:
            currency_converter: Currency converter instance
            institution_config: Institution configuration from YAML
        """
        self.converter = currency_converter
        self.config = institution_config
        self.institution_name = institution_config.get('institution', {}).get('name', 'Unknown')

        # Transaction ID sequence counter
        self.transaction_sequence = defaultdict(int)

        logger.debug(f"Initialized normalizer for {self.institution_name}")

    def normalize_transactions(
        self,
        raw_transactions: List[Dict[str, Any]],
        source_file: str
    ) -> List[Transaction]:
        """
        Normalize a list of raw transactions.

        Args:
            raw_transactions: List of raw transaction dictionaries
            source_file: Source filename

        Returns:
            List of Transaction objects
        """
        transactions = []

        for i, raw_txn in enumerate(raw_transactions):
            try:
                txn = self.normalize_transaction(raw_txn, source_file)
                if txn:
                    transactions.append(txn)
            except Exception as e:
                logger.warning(f"Failed to normalize transaction {i+1}: {str(e)}")
                logger.debug(f"Raw transaction: {raw_txn}")

        logger.info(f"Normalized {len(transactions)} out of {len(raw_transactions)} transactions")
        return transactions

    def _clean_string_field(self, value: Any) -> str:
        """
        Clean string field by removing quotes and empty strings.

        Args:
            value: Raw field value

        Returns:
            Cleaned string or empty string
        """
        if not value:
            return ''

        # Convert to string and strip
        cleaned = str(value).strip()

        # Strip quotes
        cleaned = cleaned.strip('"').strip("'")

        # If result is empty, just quotes, or just a single "/", return empty string
        if not cleaned or cleaned == '""' or cleaned == "''" or cleaned == '/':
            return ''

        return cleaned

    def normalize_transaction(
        self,
        raw_data: Dict[str, Any],
        source_file: str
    ) -> Optional[Transaction]:
        """
        Convert raw transaction dict to Transaction object.

        Args:
            raw_data: Raw transaction dictionary from parser
            source_file: Source filename

        Returns:
            Transaction object or None if invalid
        """
        # Parse date
        date = self._parse_date(raw_data.get('date', ''))
        if not date:
            logger.warning(f"Invalid date: {raw_data.get('date')}")
            return None

        # Parse amount (try 'amount' first, then 'amount_raw' for Wise)
        amount_str = raw_data.get('amount') or raw_data.get('amount_raw', '0')
        amount = self._parse_amount(amount_str, raw_data)
        if amount is None:
            logger.warning(f"Invalid amount: {amount_str}")
            return None

        # Get currency (strip quotes)
        currency_raw = str(raw_data.get('currency', 'CZK')).strip().strip('"').strip("'")
        currency = normalize_currency_code(currency_raw)

        # Convert to CZK (base currency)
        try:
            amount_czk = self.converter.convert(amount, currency, 'CZK')
        except Exception as e:
            logger.warning(f"Currency conversion failed: {e}")
            amount_czk = amount  # Fallback to original

        # Calculate the actual exchange rate used (amount_czk / amount)
        # This gives us: 1 foreign currency = X CZK
        if currency != 'CZK' and amount != 0:
            actual_exchange_rate = amount_czk / amount
        else:
            actual_exchange_rate = Decimal('1.0')

        # Get description
        description = self._get_description(raw_data)

        # Get account (cleaned)
        account = self._clean_string_field(raw_data.get('account', ''))

        # Determine owner
        owner = self._determine_owner(raw_data, account)

        # Map category
        category = self._apply_category_mapping(raw_data)

        # Generate transaction ID
        transaction_id = self._generate_transaction_id(date)

        # Get transaction type
        transaction_type = self._get_transaction_type(raw_data, amount)

        # Wise-specific: Use Source name for IN transfers, Target name for OUT
        counterparty_name_value = self._clean_string_field(raw_data.get('counterparty_name', ''))
        if self.institution_name == "Wise":
            direction = raw_data.get('_direction', raw_data.get('direction', ''))
            if direction == 'IN':
                # For incoming transfers, the sender is in Source name
                source_name = self._clean_string_field(raw_data.get('_source_name', ''))
                if source_name:
                    counterparty_name_value = source_name
                    logger.debug(f"Wise IN transfer: using Source name '{source_name}' as counterparty")

        # Create Transaction object
        transaction = Transaction(
            date=date,
            description=description,
            amount=amount,
            currency=currency,
            amount_czk=amount_czk,
            category=category,
            account=account,
            institution=self.institution_name,
            owner=owner,
            transaction_type=transaction_type,
            source_file=source_file,
            transaction_id=transaction_id,
            processed_date=datetime.now(),
            # Optional fields (cleaned)
            counterparty_account=self._clean_string_field(raw_data.get('counterparty_account', '')),
            counterparty_name=counterparty_name_value,
            counterparty_bank=self._clean_string_field(raw_data.get('counterparty_bank', '')),
            reference=self._clean_string_field(raw_data.get('reference', '')),
            variable_symbol=self._clean_string_field(raw_data.get('variable_symbol', '')),
            constant_symbol=self._clean_string_field(raw_data.get('constant_symbol', '')),
            specific_symbol=self._clean_string_field(raw_data.get('specific_symbol', '')),
            note=self._clean_string_field(raw_data.get('note', '')),
            exchange_rate=actual_exchange_rate
        )

        return transaction

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date from various formats.

        Handles:
        - "31.10.2025" (ČSOB)
        - "27. 10. 2025" (Partners)
        - "2025-11-03 21:51:17" (Wise)
        """
        if not date_str:
            return None

        # Remove quotes if present
        date_str = str(date_str).strip().strip('"').strip("'")

        # Get date format from config
        transformations = self.config.get('transformations', {})
        date_config = transformations.get('date', {})
        date_format = date_config.get('format')

        # Try parsing with configured format first
        if date_format:
            parsed = parse_date(date_str, date_format=date_format)
            if parsed:
                return parsed

        # Try Czech date parser (handles dots and spaces)
        parsed = parse_czech_date(date_str)
        if parsed:
            return parsed

        # Try generic parser
        parsed = parse_date(date_str)
        if parsed:
            return parsed

        return None

    def _parse_amount(
        self,
        amount_str: str,
        raw_data: Dict[str, Any]
    ) -> Optional[Decimal]:
        """
        Parse amount with different decimal/thousands separators.

        Handles:
        - "-1100,00" (ČSOB)
        - "14 00000" or "-86149" (Partners)
        - "12.50" (Wise)
        """
        if not amount_str:
            return Decimal('0')

        # Remove quotes and clean
        amount_str = str(amount_str).strip().strip('"').strip("'")

        # Handle encoding issues (like \xa0 non-breaking space)
        amount_str = amount_str.replace('\xa0', '').replace('\u00a0', '')

        # Get transformations config
        transformations = self.config.get('transformations', {})
        amount_config = transformations.get('amount', {})

        decimal_sep = amount_config.get('decimal_separator', '.')
        thousands_sep = amount_config.get('thousands_separator', '')
        reverse_sign = amount_config.get('reverse_sign', False)

        try:
            # Remove currency symbols
            amount_str = re.sub(r'[^\d\-+.,\s]', '', amount_str)

            # Remove thousands separator
            if thousands_sep:
                amount_str = amount_str.replace(thousands_sep, '')

            # Replace decimal separator with period
            if decimal_sep != '.':
                amount_str = amount_str.replace(decimal_sep, '.')

            # Clean up any remaining spaces
            amount_str = amount_str.replace(' ', '')

            # Convert to Decimal
            amount = Decimal(amount_str)

            # Reverse sign if needed (for some institutions)
            if reverse_sign:
                amount = -amount

            # Handle direction field (Wise: OUT/IN, Partners: Odchozí/Příchozí)
            if 'direction' in raw_data or '_direction' in raw_data:
                direction = raw_data.get('direction', raw_data.get('_direction', ''))
                # Wise: OUT/IN
                if direction == 'OUT' and amount > 0:
                    amount = -amount
                elif direction == 'IN' and amount < 0:
                    amount = -amount
                # Partners Bank: Odchozí/Příchozí
                elif direction == 'Odchozí' and amount > 0:
                    amount = -amount
                elif direction == 'Příchozí' and amount < 0:
                    amount = -amount

            return amount

        except (InvalidOperation, ValueError) as e:
            logger.error(f"Failed to parse amount '{amount_str}': {e}")
            return None

    def _get_description(self, raw_data: Dict[str, Any]) -> str:
        """
        Get transaction description.

        Falls back through multiple fields if primary is empty.
        """
        transformations = self.config.get('transformations', {})
        desc_config = transformations.get('description', {})

        # Check for fallback fields
        fallback_fields = desc_config.get('fallback_fields', ['description'])

        for field in fallback_fields:
            value = raw_data.get(field, '')
            if value:
                # Clean up
                value = str(value).strip().strip('"').strip("'")

                # Strip whitespace if configured
                if desc_config.get('strip_whitespace'):
                    value = ' '.join(value.split())

                # Remove patterns if configured
                remove_patterns = desc_config.get('remove_patterns', [])
                for pattern in remove_patterns:
                    value = re.sub(pattern, '', value)

                # Clean up empty brackets from combined descriptions
                # Remove patterns like [Msg: ], [Note: ], [Ref: ]
                value = re.sub(r'\[Msg:\s*\]', '', value)
                value = re.sub(r'\[Note:\s*\]', '', value)
                value = re.sub(r'\[Ref:\s*\]', '', value)

                # Clean up extra spaces and trim
                value = ' '.join(value.split())

                return value.strip()

        # Default fallback
        return raw_data.get('description', 'Unknown')

    def _determine_owner(self, raw_data: Dict[str, Any], account: str) -> str:
        """
        Determine transaction owner based on account mapping.
        """
        owner_config = self.config.get('owner_detection', {})
        method = owner_config.get('method', 'account_mapping')

        if method == 'account_mapping':
            account_mapping = owner_config.get('account_mapping', {})

            # Try exact match
            if account in account_mapping:
                return account_mapping[account]

            # Try without bank code (e.g., "283337817/0300" -> "283337817")
            account_base = account.split('/')[0] if '/' in account else account
            if account_base in account_mapping:
                return account_mapping[account_base]

        # Try from raw data
        if 'owner' in raw_data:
            return raw_data['owner']

        # Default
        return owner_config.get('default_owner', 'Unknown')

    def _apply_category_mapping(self, raw_data: Dict[str, Any]) -> str:
        """
        Map institution category to standard category.
        """
        category_mapping = self.config.get('category_mapping', {})

        # Get source category (cleaned)
        source_category = self._clean_string_field(raw_data.get('category_source', raw_data.get('category', '')))

        if not source_category:
            # Try transaction type (cleaned)
            source_category = self._clean_string_field(raw_data.get('transaction_type', ''))

        # Map to standard category
        if source_category in category_mapping:
            return category_mapping[source_category]

        # Return as-is or default
        return source_category if source_category else 'Uncategorized'

    def _generate_transaction_id(self, date: datetime) -> str:
        """
        Generate unique transaction ID.

        Format: TXN_YYYYMMDD_XXX
        """
        date_str = date.strftime('%Y%m%d')

        # Increment sequence for this date
        self.transaction_sequence[date_str] += 1
        sequence = self.transaction_sequence[date_str]

        return f"TXN_{date_str}_{sequence:03d}"

    def _get_transaction_type(self, raw_data: Dict[str, Any], amount: Decimal) -> str:
        """
        Determine transaction type (Debit/Credit/Transfer).
        """
        # Check if type is provided (clean it first)
        txn_type = self._clean_string_field(raw_data.get('transaction_type', ''))
        if txn_type:
            return txn_type

        # Determine from amount
        if amount < 0:
            return 'Debit'
        elif amount > 0:
            return 'Credit'
        else:
            return 'Zero'

    def _parse_exchange_rate(self, rate_str: str) -> Optional[Decimal]:
        """Parse exchange rate if present."""
        if not rate_str:
            return None

        try:
            rate_str = str(rate_str).strip().strip('"').strip("'")
            rate_str = rate_str.replace(',', '.')
            return Decimal(rate_str)
        except (InvalidOperation, ValueError):
            return None
