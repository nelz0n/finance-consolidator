"""Test CNB API integration."""

import sys
sys.path.insert(0, '.')

from src.utils.cnb_api import CNBExchangeRates
from decimal import Decimal

print("=" * 80)
print("Testing CNB API Integration")
print("=" * 80)

# Initialize CNB API
print("\n1. Initializing CNB API...")
cnb = CNBExchangeRates(cache_dir="data/cache")

# Fetch today's rates
print("\n2. Fetching current exchange rates...")
rates = cnb.fetch_rates()

print(f"\nFetched {len(rates)} exchange rates:")
print(f"  EUR: {rates.get('EUR', 'N/A')} CZK")
print(f"  USD: {rates.get('USD', 'N/A')} CZK")
print(f"  GBP: {rates.get('GBP', 'N/A')} CZK")
print(f"  PLN: {rates.get('PLN', 'N/A')} CZK")

# Test conversion
print("\n3. Testing conversions...")
print(f"  100 EUR = {cnb.convert_to_czk(Decimal('100'), 'EUR'):.2f} CZK")
print(f"  100 USD = {cnb.convert_to_czk(Decimal('100'), 'USD'):.2f} CZK")
print(f"  1000 CZK = {cnb.convert_from_czk(Decimal('1000'), 'EUR'):.2f} EUR")

# Show all supported currencies
print("\n4. Supported currencies:")
currencies = cnb.get_all_supported_currencies()
print(f"  Total: {len(currencies)} currencies")
print(f"  Sample: {', '.join(currencies[:10])}...")

print("\n" + "=" * 80)
print("✅ CNB API test completed successfully!")
print("=" * 80)
