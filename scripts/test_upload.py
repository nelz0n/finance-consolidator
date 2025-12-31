"""Test script to debug transaction upload issue"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.parser import FileParser
from src.core.normalizer import DataNormalizer
from backend.database.connection import get_db_context
from backend.database.models import Transaction as DBTransaction

# Parse a sample file
file_path = "data/uploads/csob_20251230_202330.csv"  # Use most recent upload

print(f"Parsing file: {file_path}")

# Load CSOB institution config
import yaml
with open("config/institutions/csob.yaml", "r", encoding="utf-8") as f:
    csob_config = yaml.safe_load(f)

parser = FileParser(csob_config)
parsed_data = parser.parse_file(file_path)
print(f"Parsed {len(parsed_data)} rows")

# Normalize
from src.utils.cnb_api import CNBExchangeRates
currency_converter = CNBExchangeRates()
normalizer = DataNormalizer(currency_converter, csob_config)
transactions = normalizer.normalize_transactions(parsed_data, file_path)
print(f"Normalized {len(transactions)} transactions")

# Check for duplicate transaction IDs
transaction_ids = [txn.transaction_id for txn in transactions]
print(f"\nTotal transaction IDs: {len(transaction_ids)}")
print(f"Unique transaction IDs: {len(set(transaction_ids))}")

# Find duplicates
from collections import Counter
id_counts = Counter(transaction_ids)
duplicates = {tid: count for tid, count in id_counts.items() if count > 1}

if duplicates:
    print(f"\n❌ FOUND DUPLICATES:")
    for tid, count in duplicates.items():
        print(f"  {tid}: appears {count} times")
        # Show which transactions have this ID
        for i, txn in enumerate(transactions):
            if txn.transaction_id == tid:
                print(f"    Transaction {i}: date={txn.date}, amount={txn.amount}, desc={txn.description[:50]}")
else:
    print("\n✓ No duplicate transaction IDs found")
    print("\nFirst 5 transaction IDs:")
    for i, tid in enumerate(transaction_ids[:5]):
        print(f"  {i+1}. {tid}")
