"""Unit tests for CurrencyConverter."""

import unittest
from decimal import Decimal
from src.utils.currency import CurrencyConverter, normalize_currency_code


class TestCurrencyConverter(unittest.TestCase):
    """Test cases for CurrencyConverter class."""

    def setUp(self):
        """Set up test fixtures."""
        self.rates = {
            'EUR': 1.0,
            'CZK': 25.0,
            'USD': 1.1
        }
        self.converter = CurrencyConverter(
            rates=self.rates,
            base_currency='CZK'
        )

    def test_converter_initialization(self):
        """Test converter initializes correctly."""
        self.assertIsNotNone(self.converter)
        self.assertEqual(self.converter.base_currency, 'CZK')
        self.assertEqual(self.converter.rates, self.rates)

    def test_convert_czk_to_eur(self):
        """Test converting CZK to EUR."""
        # 100 CZK = 4 EUR (100 / 25 * 1.0)
        result = self.converter.convert(Decimal('100'), 'CZK', 'EUR')
        self.assertEqual(result, Decimal('4.00'))

    def test_convert_eur_to_czk(self):
        """Test converting EUR to CZK."""
        # 4 EUR = 100 CZK (4 / 1.0 * 25)
        result = self.converter.convert(Decimal('4'), 'EUR', 'CZK')
        self.assertEqual(result, Decimal('100.00'))

    def test_convert_same_currency(self):
        """Test converting same currency returns same amount."""
        result = self.converter.convert(Decimal('100'), 'EUR', 'EUR')
        self.assertEqual(result, Decimal('100'))

    def test_convert_czk_to_usd(self):
        """Test converting CZK to USD through base currency."""
        # 25 CZK = 1 EUR = 1.1 USD
        result = self.converter.convert(Decimal('25'), 'CZK', 'USD')
        self.assertEqual(result, Decimal('1.10'))

    def test_convert_negative_amount(self):
        """Test converting negative amounts."""
        result = self.converter.convert(Decimal('-100'), 'CZK', 'EUR')
        self.assertEqual(result, Decimal('-4.00'))

    def test_convert_zero_amount(self):
        """Test converting zero amount."""
        result = self.converter.convert(Decimal('0'), 'CZK', 'EUR')
        self.assertEqual(result, Decimal('0'))

    def test_convert_with_precision(self):
        """Test conversion maintains precision."""
        result = self.converter.convert(Decimal('33.33'), 'CZK', 'EUR')
        # 33.33 / 25 = 1.3332
        self.assertEqual(result, Decimal('1.33'))

    def test_convert_large_amount(self):
        """Test converting large amounts."""
        result = self.converter.convert(Decimal('1000000'), 'CZK', 'EUR')
        self.assertEqual(result, Decimal('40000.00'))

    def test_convert_to_eur(self):
        """Test convert_to_eur convenience method."""
        result = self.converter.convert_to_eur(Decimal('100'), 'CZK')
        self.assertEqual(result, Decimal('4.00'))

    def test_convert_to_eur_from_eur(self):
        """Test convert_to_eur when already in EUR."""
        result = self.converter.convert_to_eur(Decimal('100'), 'EUR')
        self.assertEqual(result, Decimal('100'))

    def test_convert_unknown_currency(self):
        """Test converting unknown currency raises error."""
        with self.assertRaises(ValueError):
            self.converter.convert(Decimal('100'), 'XXX', 'EUR')

    def test_convert_to_unknown_currency(self):
        """Test converting to unknown currency raises error."""
        with self.assertRaises(ValueError):
            self.converter.convert(Decimal('100'), 'EUR', 'XXX')

    def test_get_rate(self):
        """Test getting exchange rate."""
        rate = self.converter.get_rate('EUR')
        self.assertEqual(rate, Decimal('1.0'))

        rate = self.converter.get_rate('CZK')
        self.assertEqual(rate, Decimal('25.0'))

    def test_get_rate_unknown_currency(self):
        """Test getting rate for unknown currency raises error."""
        with self.assertRaises(ValueError):
            self.converter.get_rate('XXX')

    def test_normalize_currency_code(self):
        """Test currency code normalization."""
        self.assertEqual(normalize_currency_code('eur'), 'EUR')
        self.assertEqual(normalize_currency_code('EUR'), 'EUR')
        self.assertEqual(normalize_currency_code('Eur'), 'EUR')
        self.assertEqual(normalize_currency_code('czk'), 'CZK')

    def test_normalize_currency_code_strips_whitespace(self):
        """Test currency code normalization strips whitespace."""
        self.assertEqual(normalize_currency_code(' EUR '), 'EUR')
        self.assertEqual(normalize_currency_code('  czk  '), 'CZK')

    def test_converter_with_different_base_currency(self):
        """Test converter with EUR as base currency."""
        converter = CurrencyConverter(
            rates={'EUR': 1.0, 'CZK': 25.0},
            base_currency='EUR'
        )

        result = converter.convert(Decimal('25'), 'CZK', 'EUR')
        self.assertEqual(result, Decimal('1.00'))

    def test_multiple_conversions_consistency(self):
        """Test that multiple conversions are consistent."""
        # Convert 100 CZK -> EUR -> USD -> EUR -> CZK
        amount1 = self.converter.convert(Decimal('100'), 'CZK', 'EUR')
        amount2 = self.converter.convert(amount1, 'EUR', 'USD')
        amount3 = self.converter.convert(amount2, 'USD', 'EUR')
        amount4 = self.converter.convert(amount3, 'EUR', 'CZK')

        # Should be close to original (within rounding)
        self.assertAlmostEqual(float(amount4), 100.0, places=1)

    def test_string_amount_conversion(self):
        """Test that string amounts are handled."""
        # Converter should accept strings and convert to Decimal
        result = self.converter.convert('100', 'CZK', 'EUR')
        self.assertEqual(result, Decimal('4.00'))

    def test_float_amount_conversion(self):
        """Test that float amounts are handled."""
        result = self.converter.convert(100.0, 'CZK', 'EUR')
        self.assertEqual(result, Decimal('4.00'))


class TestNormalizeCurrencyCode(unittest.TestCase):
    """Test cases for normalize_currency_code function."""

    def test_normalize_uppercase(self):
        """Test normalizing uppercase codes."""
        self.assertEqual(normalize_currency_code('EUR'), 'EUR')
        self.assertEqual(normalize_currency_code('CZK'), 'CZK')
        self.assertEqual(normalize_currency_code('USD'), 'USD')

    def test_normalize_lowercase(self):
        """Test normalizing lowercase codes."""
        self.assertEqual(normalize_currency_code('eur'), 'EUR')
        self.assertEqual(normalize_currency_code('czk'), 'CZK')
        self.assertEqual(normalize_currency_code('usd'), 'USD')

    def test_normalize_mixed_case(self):
        """Test normalizing mixed case codes."""
        self.assertEqual(normalize_currency_code('Eur'), 'EUR')
        self.assertEqual(normalize_currency_code('CzK'), 'CZK')

    def test_normalize_with_whitespace(self):
        """Test normalizing codes with whitespace."""
        self.assertEqual(normalize_currency_code(' EUR '), 'EUR')
        self.assertEqual(normalize_currency_code('  CZK  '), 'CZK')
        self.assertEqual(normalize_currency_code('\tUSD\n'), 'USD')


if __name__ == '__main__':
    unittest.main()
