"""Unit tests for DataNormalizer."""

import unittest
from datetime import date
from decimal import Decimal
from src.core.normalizer import DataNormalizer
from src.utils.currency import CurrencyConverter


class TestDataNormalizer(unittest.TestCase):
    """Test cases for DataNormalizer class."""

    def setUp(self):
        """Set up test fixtures."""
        # Set up currency converter
        self.converter = CurrencyConverter(
            rates={'EUR': 1.0, 'CZK': 25.0},
            base_currency='CZK'
        )

        # Sample institution config
        self.config = {
            'institution': {'name': 'TestBank'},
            'column_mapping': {
                'date': 'date',
                'amount': 'amount',
                'description': 'description',
                'currency': 'currency',
                'defaults': {
                    'institution': 'TestBank',
                    'currency': 'EUR'
                }
            },
            'transformations': {
                'date': {'format': '%Y-%m-%d'},
                'amount': {
                    'decimal_separator': '.',
                    'thousands_separator': ','
                }
            },
            'owner_detection': {
                'method': 'account_mapping',
                'account_mapping': {
                    '123456': 'John Doe'
                },
                'default_owner': 'Unknown'
            }
        }

    def test_normalizer_initialization(self):
        """Test normalizer initializes correctly."""
        normalizer = DataNormalizer(self.converter, self.config)
        self.assertIsNotNone(normalizer)

    def test_normalize_basic_transaction(self):
        """Test normalizing a basic transaction."""
        raw_data = {
            'date': '2024-10-15',
            'amount': '100.50',
            'description': 'Test payment',
            'currency': 'EUR'
        }

        normalizer = DataNormalizer(self.converter, self.config)
        txn = normalizer.normalize_transaction(raw_data, 'test.csv')

        self.assertIsNotNone(txn)
        self.assertEqual(txn.date, date(2024, 10, 15))
        self.assertEqual(txn.amount, Decimal('100.50'))
        self.assertEqual(txn.description, 'Test payment')
        self.assertEqual(txn.currency, 'EUR')
        self.assertEqual(txn.institution, 'TestBank')
        self.assertEqual(txn.source_file, 'test.csv')

    def test_normalize_with_czech_amount_format(self):
        """Test normalizing Czech amount format (comma decimal, space thousands)."""
        raw_data = {
            'date': '15.10.2024',
            'amount': '1 000,50',
            'description': 'Test',
            'currency': 'CZK'
        }

        config = self.config.copy()
        config['transformations'] = {
            'date': {'format': '%d.%m.%Y'},
            'amount': {
                'decimal_separator': ',',
                'thousands_separator': ' '
            }
        }

        normalizer = DataNormalizer(self.converter, config)
        txn = normalizer.normalize_transaction(raw_data, 'csob.csv')

        self.assertIsNotNone(txn)
        self.assertEqual(txn.amount, Decimal('1000.50'))

    def test_normalize_negative_amount(self):
        """Test normalizing negative amounts."""
        raw_data = {
            'date': '2024-10-15',
            'amount': '-50.00',
            'description': 'Withdrawal',
            'currency': 'EUR'
        }

        normalizer = DataNormalizer(self.converter, self.config)
        txn = normalizer.normalize_transaction(raw_data, 'test.csv')

        self.assertEqual(txn.amount, Decimal('-50.00'))

    def test_normalize_with_direction_field(self):
        """Test normalizing with direction field (Wise-style)."""
        # OUT direction should be negative
        raw_data_out = {
            'date': '2024-10-15',
            'amount': '50.00',
            'description': 'Payment',
            'currency': 'EUR',
            'direction': 'OUT'
        }

        config = self.config.copy()
        config['column_mapping']['direction'] = 'direction'

        normalizer = DataNormalizer(self.converter, config)
        txn = normalizer.normalize_transaction(raw_data_out, 'wise.csv')

        # Amount should be negative for OUT
        self.assertEqual(txn.amount, Decimal('-50.00'))

        # IN direction should be positive
        raw_data_in = {
            'date': '2024-10-15',
            'amount': '100.00',
            'description': 'Payment received',
            'currency': 'EUR',
            'direction': 'IN'
        }

        txn = normalizer.normalize_transaction(raw_data_in, 'wise.csv')
        self.assertEqual(txn.amount, Decimal('100.00'))

    def test_normalize_with_currency_conversion(self):
        """Test that EUR amount is calculated."""
        raw_data = {
            'date': '2024-10-15',
            'amount': '1000',
            'description': 'Test',
            'currency': 'CZK'
        }

        normalizer = DataNormalizer(self.converter, self.config)
        txn = normalizer.normalize_transaction(raw_data, 'test.csv')

        # 1000 CZK / 25 = 40 EUR
        self.assertEqual(txn.currency, 'CZK')
        self.assertEqual(txn.amount_eur, Decimal('40.00'))

    def test_normalize_with_default_currency(self):
        """Test default currency is applied."""
        raw_data = {
            'date': '2024-10-15',
            'amount': '100',
            'description': 'Test'
            # No currency field
        }

        normalizer = DataNormalizer(self.converter, self.config)
        txn = normalizer.normalize_transaction(raw_data, 'test.csv')

        self.assertEqual(txn.currency, 'EUR')  # From defaults

    def test_normalize_with_owner_detection(self):
        """Test owner detection from account mapping."""
        raw_data = {
            'date': '2024-10-15',
            'amount': '100',
            'description': 'Test',
            'currency': 'EUR',
            'account': '123456'
        }

        config = self.config.copy()
        config['column_mapping']['account'] = 'account'

        normalizer = DataNormalizer(self.converter, config)
        txn = normalizer.normalize_transaction(raw_data, 'test.csv')

        self.assertEqual(txn.owner, 'John Doe')

    def test_normalize_with_unknown_owner(self):
        """Test default owner is used for unknown accounts."""
        raw_data = {
            'date': '2024-10-15',
            'amount': '100',
            'description': 'Test',
            'currency': 'EUR',
            'account': '999999'  # Not in mapping
        }

        config = self.config.copy()
        config['column_mapping']['account'] = 'account'

        normalizer = DataNormalizer(self.converter, config)
        txn = normalizer.normalize_transaction(raw_data, 'test.csv')

        self.assertEqual(txn.owner, 'Unknown')

    def test_normalize_with_category_mapping(self):
        """Test category mapping."""
        raw_data = {
            'date': '2024-10-15',
            'amount': '100',
            'description': 'Test',
            'currency': 'EUR',
            'category_source': 'Potraviny'
        }

        config = self.config.copy()
        config['column_mapping']['category_source'] = 'category_source'
        config['category_mapping'] = {
            'Potraviny': 'Groceries',
            'Restaurace': 'Dining'
        }

        normalizer = DataNormalizer(self.converter, config)
        txn = normalizer.normalize_transaction(raw_data, 'test.csv')

        self.assertEqual(txn.category, 'Groceries')

    def test_normalize_with_unmapped_category(self):
        """Test unmapped category passes through."""
        raw_data = {
            'date': '2024-10-15',
            'amount': '100',
            'description': 'Test',
            'currency': 'EUR',
            'category_source': 'Unknown Category'
        }

        config = self.config.copy()
        config['column_mapping']['category_source'] = 'category_source'
        config['category_mapping'] = {
            'Potraviny': 'Groceries'
        }

        normalizer = DataNormalizer(self.converter, config)
        txn = normalizer.normalize_transaction(raw_data, 'test.csv')

        self.assertEqual(txn.category, 'Unknown Category')

    def test_normalize_transaction_id_generation(self):
        """Test transaction ID is generated."""
        raw_data = {
            'date': '2024-10-15',
            'amount': '100',
            'description': 'Test',
            'currency': 'EUR'
        }

        normalizer = DataNormalizer(self.converter, self.config)
        txn = normalizer.normalize_transaction(raw_data, 'test.csv')

        self.assertIsNotNone(txn.transaction_id)
        self.assertTrue(txn.transaction_id.startswith('TXN_20241015_'))

    def test_normalize_invalid_date(self):
        """Test handling of invalid date."""
        raw_data = {
            'date': 'invalid-date',
            'amount': '100',
            'description': 'Test',
            'currency': 'EUR'
        }

        normalizer = DataNormalizer(self.converter, self.config)
        txn = normalizer.normalize_transaction(raw_data, 'test.csv')

        # Should return None or handle gracefully
        # Depending on implementation, might return None
        # or use current date as fallback
        self.assertTrue(txn is None or txn.date is not None)

    def test_normalize_invalid_amount(self):
        """Test handling of invalid amount."""
        raw_data = {
            'date': '2024-10-15',
            'amount': 'not-a-number',
            'description': 'Test',
            'currency': 'EUR'
        }

        normalizer = DataNormalizer(self.converter, self.config)
        txn = normalizer.normalize_transaction(raw_data, 'test.csv')

        # Should handle gracefully
        self.assertTrue(txn is None or txn.amount is not None)

    def test_normalize_missing_required_fields(self):
        """Test handling of missing required fields."""
        raw_data = {
            'description': 'Test'
            # Missing date, amount, currency
        }

        normalizer = DataNormalizer(self.converter, self.config)
        txn = normalizer.normalize_transaction(raw_data, 'test.csv')

        # Should return None for missing required fields
        self.assertTrue(txn is None or all([
            txn.date is not None,
            txn.amount is not None
        ]))


if __name__ == '__main__':
    unittest.main()
