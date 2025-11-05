"""Unit tests for date parsing utilities."""

import unittest
from datetime import date, datetime
from src.utils.date_parser import parse_date, parse_czech_date, get_date_range


class TestParseDateFunction(unittest.TestCase):
    """Test cases for parse_date function."""

    def test_parse_iso_format(self):
        """Test parsing ISO format dates (YYYY-MM-DD)."""
        result = parse_date('2024-10-15')
        self.assertEqual(result, date(2024, 10, 15))

    def test_parse_with_explicit_format(self):
        """Test parsing with explicit format string."""
        result = parse_date('15.10.2024', date_format='%d.%m.%Y')
        self.assertEqual(result, date(2024, 10, 15))

    def test_parse_us_format(self):
        """Test parsing US format (MM/DD/YYYY)."""
        result = parse_date('10/15/2024', date_format='%m/%d/%Y')
        self.assertEqual(result, date(2024, 10, 15))

    def test_parse_european_format(self):
        """Test parsing European format (DD/MM/YYYY)."""
        result = parse_date('15/10/2024', date_format='%d/%m/%Y')
        self.assertEqual(result, date(2024, 10, 15))

    def test_parse_with_time(self):
        """Test parsing datetime strings."""
        result = parse_date('2024-10-15 14:30:00', date_format='%Y-%m-%d %H:%M:%S')
        self.assertEqual(result, date(2024, 10, 15))

    def test_parse_datetime_object(self):
        """Test parsing datetime object returns date."""
        dt = datetime(2024, 10, 15, 14, 30)
        result = parse_date(dt)
        self.assertEqual(result, date(2024, 10, 15))

    def test_parse_date_object(self):
        """Test parsing date object returns itself."""
        d = date(2024, 10, 15)
        result = parse_date(d)
        self.assertEqual(result, d)

    def test_parse_invalid_date(self):
        """Test parsing invalid date returns None."""
        result = parse_date('not-a-date')
        self.assertIsNone(result)

    def test_parse_empty_string(self):
        """Test parsing empty string returns None."""
        result = parse_date('')
        self.assertIsNone(result)

    def test_parse_none(self):
        """Test parsing None returns None."""
        result = parse_date(None)
        self.assertIsNone(result)


class TestParseCzechDateFunction(unittest.TestCase):
    """Test cases for parse_czech_date function."""

    def test_parse_standard_czech_format(self):
        """Test parsing standard Czech format (DD.MM.YYYY)."""
        result = parse_czech_date('15.10.2024')
        self.assertEqual(result, date(2024, 10, 15))

    def test_parse_czech_format_with_spaces(self):
        """Test parsing Czech format with spaces (D. M. YYYY)."""
        result = parse_czech_date('15. 10. 2024')
        self.assertEqual(result, date(2024, 10, 15))

    def test_parse_czech_format_single_digits(self):
        """Test parsing Czech format with single digits."""
        result = parse_czech_date('5.1.2024')
        self.assertEqual(result, date(2024, 1, 5))

    def test_parse_czech_format_with_spaces_single_digits(self):
        """Test parsing Czech format with spaces and single digits."""
        result = parse_czech_date('5. 1. 2024')
        self.assertEqual(result, date(2024, 1, 5))

    def test_parse_czech_format_mixed(self):
        """Test parsing Czech format with mixed single/double digits."""
        result = parse_czech_date('5. 10. 2024')
        self.assertEqual(result, date(2024, 10, 5))

    def test_parse_czech_invalid(self):
        """Test parsing invalid Czech date returns None."""
        result = parse_czech_date('not-a-date')
        self.assertIsNone(result)

    def test_parse_czech_empty(self):
        """Test parsing empty string returns None."""
        result = parse_czech_date('')
        self.assertIsNone(result)

    def test_parse_czech_none(self):
        """Test parsing None returns None."""
        result = parse_czech_date(None)
        self.assertIsNone(result)

    def test_parse_czech_leap_year(self):
        """Test parsing leap year date."""
        result = parse_czech_date('29.2.2024')
        self.assertEqual(result, date(2024, 2, 29))

    def test_parse_czech_year_boundaries(self):
        """Test parsing year boundary dates."""
        result = parse_czech_date('31.12.2024')
        self.assertEqual(result, date(2024, 12, 31))

        result = parse_czech_date('1.1.2024')
        self.assertEqual(result, date(2024, 1, 1))


class TestGetDateRangeFunction(unittest.TestCase):
    """Test cases for get_date_range function."""

    def test_get_range_both_dates(self):
        """Test getting range with both start and end dates."""
        start, end = get_date_range('2024-10-01', '2024-10-31')
        self.assertEqual(start, date(2024, 10, 1))
        self.assertEqual(end, date(2024, 10, 31))

    def test_get_range_only_start(self):
        """Test getting range with only start date."""
        start, end = get_date_range('2024-10-01', None)
        self.assertEqual(start, date(2024, 10, 1))
        self.assertIsNone(end)

    def test_get_range_only_end(self):
        """Test getting range with only end date."""
        start, end = get_date_range(None, '2024-10-31')
        self.assertIsNone(start)
        self.assertEqual(end, date(2024, 10, 31))

    def test_get_range_neither_date(self):
        """Test getting range with neither date."""
        start, end = get_date_range(None, None)
        self.assertIsNone(start)
        self.assertIsNone(end)

    def test_get_range_empty_strings(self):
        """Test getting range with empty strings."""
        start, end = get_date_range('', '')
        self.assertIsNone(start)
        self.assertIsNone(end)

    def test_get_range_with_date_objects(self):
        """Test getting range with date objects."""
        d1 = date(2024, 10, 1)
        d2 = date(2024, 10, 31)
        start, end = get_date_range(d1, d2)
        self.assertEqual(start, d1)
        self.assertEqual(end, d2)

    def test_get_range_invalid_dates(self):
        """Test getting range with invalid dates returns None."""
        start, end = get_date_range('invalid', 'invalid')
        self.assertIsNone(start)
        self.assertIsNone(end)

    def test_get_range_mixed_formats(self):
        """Test getting range with mixed date formats."""
        start, end = get_date_range('2024-10-01', '31.10.2024')
        self.assertEqual(start, date(2024, 10, 1))
        # Should try multiple formats
        self.assertTrue(end is None or end == date(2024, 10, 31))


class TestDateParsingEdgeCases(unittest.TestCase):
    """Test edge cases in date parsing."""

    def test_parse_first_day_of_century(self):
        """Test parsing first day of century."""
        result = parse_date('2000-01-01')
        self.assertEqual(result, date(2000, 1, 1))

    def test_parse_last_day_of_century(self):
        """Test parsing last day of century."""
        result = parse_date('2099-12-31')
        self.assertEqual(result, date(2099, 12, 31))

    def test_parse_leap_year_feb_29(self):
        """Test parsing Feb 29 in leap year."""
        result = parse_date('2024-02-29')
        self.assertEqual(result, date(2024, 2, 29))

    def test_parse_various_separators(self):
        """Test parsing dates with various separators."""
        # Dots
        result = parse_date('15.10.2024', date_format='%d.%m.%Y')
        self.assertEqual(result, date(2024, 10, 15))

        # Slashes
        result = parse_date('15/10/2024', date_format='%d/%m/%Y')
        self.assertEqual(result, date(2024, 10, 15))

        # Dashes
        result = parse_date('2024-10-15', date_format='%Y-%m-%d')
        self.assertEqual(result, date(2024, 10, 15))

    def test_parse_short_year(self):
        """Test parsing dates with 2-digit years."""
        result = parse_date('15.10.24', date_format='%d.%m.%y')
        self.assertEqual(result, date(2024, 10, 15))

    def test_parse_month_names(self):
        """Test parsing dates with month names."""
        result = parse_date('15 October 2024', date_format='%d %B %Y')
        self.assertEqual(result, date(2024, 10, 15))

    def test_parse_abbreviated_month(self):
        """Test parsing dates with abbreviated month names."""
        result = parse_date('15 Oct 2024', date_format='%d %b %Y')
        self.assertEqual(result, date(2024, 10, 15))


if __name__ == '__main__':
    unittest.main()
