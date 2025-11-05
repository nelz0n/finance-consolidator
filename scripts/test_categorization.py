"""Test categorization engine."""

import sys
sys.path.insert(0, '.')

from src.utils.categorizer import TransactionCategorizer

print("=" * 80)
print("Testing Categorization Engine")
print("=" * 80)

# Initialize categorizer
print("\n1. Initializing categorizer...")
categorizer = TransactionCategorizer(config_path="config/categorization.yaml")

print(f"  Loaded {len(categorizer.manual_rules)} manual rules")
print(f"  Own accounts: {len(categorizer.own_accounts)}")
print(f"  AI enabled: {categorizer.ai_enabled}")

# Test internal transfer detection
print("\n2. Testing internal transfer detection...")
internal_txn = {
    'description': 'Transfer to my savings',
    'counterparty_account': '210621040/0300',  # Own account
    'amount': 5000
}
tier1, tier2, tier3, is_transfer = categorizer.categorize(internal_txn)
print(f"  Transaction: {internal_txn['description']}")
print(f"  Result: {tier1} > {tier2} > {tier3}")
print(f"  Is internal transfer: {is_transfer}")
assert is_transfer == True, "Should detect internal transfer"

# Test manual rules - Grocery
print("\n3. Testing manual rules - Groceries...")
grocery_txn = {
    'description': 'ALBERT HYPERMARKET',
    'counterparty_name': 'ALBERT',
    'amount': 850.50,
    'date': '2024-11-05'
}
tier1, tier2, tier3, is_transfer = categorizer.categorize(grocery_txn)
print(f"  Transaction: {grocery_txn['description']}")
print(f"  Result: {tier1} > {tier2} > {tier3}")
assert tier1 == "Living Expenses", f"Expected 'Living Expenses', got '{tier1}'"
assert tier2 == "Groceries", f"Expected 'Groceries', got '{tier2}'"

# Test manual rules - Fuel
print("\n4. Testing manual rules - Fuel...")
fuel_txn = {
    'description': 'SHELL STATION PAYMENT',
    'counterparty_name': 'SHELL CZ',
    'amount': 1200,
    'date': '2024-11-05'
}
tier1, tier2, tier3, is_transfer = categorizer.categorize(fuel_txn)
print(f"  Transaction: {fuel_txn['description']}")
print(f"  Result: {tier1} > {tier2} > {tier3}")
assert tier1 == "Living Expenses", f"Expected 'Living Expenses', got '{tier1}'"
assert tier2 == "Transportation", f"Expected 'Transportation', got '{tier2}'"

# Test manual rules - Utilities
print("\n5. Testing manual rules - Utilities...")
util_txn = {
    'description': 'CEZ Distribuce',
    'counterparty_name': 'CEZ',
    'amount': 2500,
    'date': '2024-11-05'
}
tier1, tier2, tier3, is_transfer = categorizer.categorize(util_txn)
print(f"  Transaction: {util_txn['description']}")
print(f"  Result: {tier1} > {tier2} > {tier3}")
assert tier1 == "Living Expenses", f"Expected 'Living Expenses', got '{tier1}'"
assert tier2 == "Utilities", f"Expected 'Utilities', got '{tier2}'"

# Test uncategorized
print("\n6. Testing uncategorized transaction...")
unknown_txn = {
    'description': 'SOME UNKNOWN MERCHANT XYZ123',
    'counterparty_name': 'UNKNOWN CO',
    'amount': 999,
    'date': '2024-11-05'
}
tier1, tier2, tier3, is_transfer = categorizer.categorize(unknown_txn)
print(f"  Transaction: {unknown_txn['description']}")
print(f"  Result: {tier1} > {tier2} > {tier3}")
assert tier1 == "Uncategorized", f"Expected 'Uncategorized', got '{tier1}'"

print("\n" + "=" * 80)
print("✅ Categorization test completed successfully!")
print("=" * 80)
print("\nAll tests passed! The categorization engine is working correctly.")
