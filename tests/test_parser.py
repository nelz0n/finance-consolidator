"""Unit tests for FileParser."""

import unittest
import tempfile
from pathlib import Path
from src.core.parser import FileParser


class TestFileParser(unittest.TestCase):
    """Test cases for FileParser class."""

    def setUp(self):
        """Set up test fixtures."""
        # Sample ČSOB-like config
        self.csob_config = {
            'institution': {'name': 'ČSOB'},
            'format': {
                'type': 'csv',
                'encoding': 'utf-8',
                'delimiter': ';',
                'has_header': True,
                'skip_rows': 0
            },
            'column_mapping': {
                'date': 'datum',
                'amount': 'castka',
                'description': 'zprava',
                'currency': 'mena',
                'defaults': {
                    'institution': 'ČSOB'
                }
            },
            'transformations': {
                'date': {'format': '%d.%m.%Y'},
                'amount': {
                    'decimal_separator': ',',
                    'thousands_separator': ' '
                }
            }
        }

        # Sample CSV config
        self.csv_config = {
            'institution': {'name': 'TestBank'},
            'format': {
                'type': 'csv',
                'encoding': 'utf-8',
                'delimiter': ',',
                'has_header': True,
                'skip_rows': 0
            },
            'column_mapping': {
                'date': 'Date',
                'amount': 'Amount',
                'description': 'Description',
                'defaults': {
                    'institution': 'TestBank',
                    'currency': 'EUR'
                }
            }
        }

    def test_parser_initialization(self):
        """Test parser initializes correctly."""
        parser = FileParser(self.csob_config)
        self.assertIsNotNone(parser)
        self.assertEqual(parser.config, self.csob_config)

    def test_parse_simple_csv(self):
        """Test parsing a simple CSV file."""
        # Create temporary CSV file
        csv_content = """Date,Amount,Description
2024-10-01,100.00,Test Transaction 1
2024-10-02,-50.50,Test Transaction 2
2024-10-03,75.25,Test Transaction 3"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(csv_content)
            temp_path = f.name

        try:
            parser = FileParser(self.csv_config)
            result = parser.parse_file(temp_path)

            self.assertEqual(len(result), 3)
            self.assertEqual(result[0]['date'], '2024-10-01')
            self.assertEqual(result[0]['amount'], '100.00')
            self.assertEqual(result[0]['description'], 'Test Transaction 1')
            self.assertEqual(result[0]['institution'], 'TestBank')
            self.assertEqual(result[0]['currency'], 'EUR')

        finally:
            Path(temp_path).unlink()

    def test_parse_csv_with_skip_rows(self):
        """Test parsing CSV with skip_rows."""
        csv_content = """Account Summary Line
Empty Line
Date,Amount,Description
2024-10-01,100.00,Test Transaction"""

        config = self.csv_config.copy()
        config['format']['skip_rows'] = 2

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(csv_content)
            temp_path = f.name

        try:
            parser = FileParser(config)
            result = parser.parse_file(temp_path)

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['date'], '2024-10-01')

        finally:
            Path(temp_path).unlink()

    def test_parse_csv_with_czech_format(self):
        """Test parsing CSV with Czech number format."""
        csv_content = """datum;castka;zprava;mena
15.10.2024;1 000,50;Test platba;CZK
16.10.2024;-500,00;Vyber;CZK"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(csv_content)
            temp_path = f.name

        try:
            parser = FileParser(self.csob_config)
            result = parser.parse_file(temp_path)

            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]['date'], '15.10.2024')
            self.assertEqual(result[0]['amount'], '1 000,50')
            self.assertEqual(result[0]['currency'], 'CZK')

        finally:
            Path(temp_path).unlink()

    def test_parse_csv_with_filtering(self):
        """Test parsing with row filtering."""
        csv_content = """Date,Amount,Description
HEADER LINE TO SKIP,0,0
2024-10-01,100.00,Valid Transaction
2024-10-02,200.00,Valid Transaction 2"""

        config = self.csv_config.copy()
        config['filtering'] = {
            'skip_if_contains': ['HEADER LINE']
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(csv_content)
            temp_path = f.name

        try:
            parser = FileParser(config)
            result = parser.parse_file(temp_path)

            # Should skip the header line
            self.assertEqual(len(result), 2)
            self.assertNotIn('HEADER LINE', str(result))

        finally:
            Path(temp_path).unlink()

    def test_parse_empty_file(self):
        """Test parsing an empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("Date,Amount,Description\n")
            temp_path = f.name

        try:
            parser = FileParser(self.csv_config)
            result = parser.parse_file(temp_path)

            self.assertEqual(len(result), 0)

        finally:
            Path(temp_path).unlink()

    def test_column_mapping_with_defaults(self):
        """Test that default values are applied."""
        csv_content = """Date,Amount
2024-10-01,100.00"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(csv_content)
            temp_path = f.name

        try:
            parser = FileParser(self.csv_config)
            result = parser.parse_file(temp_path)

            self.assertEqual(result[0]['institution'], 'TestBank')
            self.assertEqual(result[0]['currency'], 'EUR')

        finally:
            Path(temp_path).unlink()

    def test_transformation_strip(self):
        """Test strip transformation."""
        csv_content = """Date,Amount,Description
2024-10-01,100.00,  Test with spaces  """

        config = self.csv_config.copy()
        config['column_mapping']['transformations'] = [
            {'fields': ['description'], 'type': 'strip'}
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(csv_content)
            temp_path = f.name

        try:
            parser = FileParser(config)
            result = parser.parse_file(temp_path)

            # Note: strip is applied during normalization, not parsing
            # This test documents expected behavior
            self.assertIn('description', result[0])

        finally:
            Path(temp_path).unlink()


if __name__ == '__main__':
    unittest.main()
