"""
Czech National Bank (CNB) API Integration
Fetches real-time exchange rates from official CNB source
"""

import requests
import logging
from decimal import Decimal
from datetime import date, datetime, timedelta
from typing import Dict, Optional
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class CNBExchangeRates:
    """
    Fetch and cache exchange rates from Czech National Bank.

    CNB publishes daily exchange rates around 2:30 PM CET.
    All rates are expressed as: 1 CZK = X foreign currency
    (or amount foreign currency = 1 CZK)

    Example CNB format:
    Country|Currency|Amount|Code|Rate
    USA|dollar|1|USD|22.795
    (meaning 1 USD = 22.795 CZK)
    """

    CNB_DAILY_URL = "https://www.cnb.cz/en/financial-markets/foreign-exchange-market/central-bank-exchange-rate-fixing/central-bank-exchange-rate-fixing/daily.txt"

    def __init__(self, cache_dir: str = "data/cache"):
        """
        Initialize CNB API client.

        Args:
            cache_dir: Directory to store cached rates
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "cnb_rates_cache.json"

        # In-memory cache
        self._rates_cache: Dict[str, Dict[str, Decimal]] = {}

        # Load from disk cache
        self._load_cache_from_disk()

    def _load_cache_from_disk(self):
        """Load cached rates from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)

                # Convert string decimals back to Decimal
                for date_str, rates in cache_data.items():
                    self._rates_cache[date_str] = {
                        code: Decimal(rate) for code, rate in rates.items()
                    }

                logger.info(f"Loaded {len(self._rates_cache)} cached rate sets from disk")
            except Exception as e:
                logger.warning(f"Could not load rate cache: {e}")

    def _save_cache_to_disk(self):
        """Save cached rates to disk."""
        try:
            # Convert Decimal to string for JSON
            cache_data = {
                date_str: {code: str(rate) for code, rate in rates.items()}
                for date_str, rates in self._rates_cache.items()
            }

            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)

            logger.debug(f"Saved rate cache to disk: {len(cache_data)} dates")
        except Exception as e:
            logger.warning(f"Could not save rate cache: {e}")

    def fetch_rates(self, target_date: Optional[date] = None) -> Dict[str, Decimal]:
        """
        Fetch exchange rates from CNB for a specific date.

        Args:
            target_date: Date to fetch rates for (default: today)

        Returns:
            Dictionary mapping currency codes to rates (CZK per 1 unit)
            Example: {'USD': Decimal('22.795'), 'EUR': Decimal('24.120')}

        Raises:
            requests.RequestException: If API request fails
        """
        if target_date is None:
            target_date = date.today()

        date_str = target_date.isoformat()

        # Check cache first
        if date_str in self._rates_cache:
            logger.debug(f"Using cached rates for {date_str}")
            return self._rates_cache[date_str]

        logger.info(f"Fetching exchange rates from CNB for {date_str}...")

        try:
            # CNB daily.txt returns today's rates (or most recent if weekend)
            response = requests.get(self.CNB_DAILY_URL, timeout=10)
            response.raise_for_status()

            rates = self._parse_cnb_response(response.text)

            # Add CZK itself (1 CZK = 1 CZK)
            rates['CZK'] = Decimal('1.0')

            # Cache the results
            self._rates_cache[date_str] = rates
            self._save_cache_to_disk()

            logger.info(f"Fetched {len(rates)} exchange rates from CNB")
            return rates

        except requests.RequestException as e:
            logger.error(f"Failed to fetch rates from CNB: {e}")

            # Try to use most recent cached rates
            if self._rates_cache:
                most_recent = max(self._rates_cache.keys())
                logger.warning(f"Using cached rates from {most_recent} as fallback")
                return self._rates_cache[most_recent]

            raise

    def _parse_cnb_response(self, text: str) -> Dict[str, Decimal]:
        """
        Parse CNB daily.txt response.

        Format:
        Line 1: Date DD Mon YYYY #XXX
        Line 2: Country|Currency|Amount|Code|Rate
        Line 3+: Data rows

        Example:
        05 Nov 2025 #215
        Country|Currency|Amount|Code|Rate
        Australia|dollar|1|AUD|14.683
        USA|dollar|1|USD|22.795
        EMU|euro|1|EUR|24.120

        Note: Some currencies have Amount > 1 (e.g., 100 JPY = X CZK)
        We normalize to rate per 1 unit.
        """
        rates = {}

        lines = text.strip().split('\n')

        # Skip first two lines (date and header)
        for line in lines[2:]:
            parts = line.split('|')
            if len(parts) != 5:
                continue

            try:
                country, currency_name, amount, code, rate = parts

                amount = int(amount)
                rate = Decimal(rate)

                # Normalize to rate per 1 unit
                # If amount = 100 and rate = 15.5, then 1 unit = 15.5/100 = 0.155 CZK
                rate_per_unit = rate / Decimal(amount)

                rates[code.strip()] = rate_per_unit

            except (ValueError, decimal.InvalidOperation) as e:
                logger.warning(f"Could not parse CNB line: {line} - {e}")
                continue

        return rates

    def get_rate(self, currency_code: str, target_date: Optional[date] = None) -> Decimal:
        """
        Get exchange rate for a specific currency.

        Args:
            currency_code: ISO currency code (e.g., 'USD', 'EUR')
            target_date: Date to get rate for (default: today)

        Returns:
            Exchange rate (CZK per 1 unit of currency)

        Raises:
            ValueError: If currency not found
        """
        rates = self.fetch_rates(target_date)

        if currency_code not in rates:
            raise ValueError(f"Currency {currency_code} not found in CNB rates")

        return rates[currency_code]

    def convert_to_czk(self, amount: Decimal, from_currency: str,
                       target_date: Optional[date] = None) -> Decimal:
        """
        Convert amount from foreign currency to CZK.

        Args:
            amount: Amount in source currency
            from_currency: Source currency code
            target_date: Date to use for exchange rate

        Returns:
            Amount in CZK
        """
        if from_currency == 'CZK':
            return amount

        rate = self.get_rate(from_currency, target_date)
        return amount * rate

    def convert_from_czk(self, amount: Decimal, to_currency: str,
                        target_date: Optional[date] = None) -> Decimal:
        """
        Convert amount from CZK to foreign currency.

        Args:
            amount: Amount in CZK
            to_currency: Target currency code
            target_date: Date to use for exchange rate

        Returns:
            Amount in target currency
        """
        if to_currency == 'CZK':
            return amount

        rate = self.get_rate(to_currency, target_date)
        return amount / rate

    def get_all_supported_currencies(self, target_date: Optional[date] = None) -> list:
        """
        Get list of all supported currency codes.

        Returns:
            List of currency codes
        """
        rates = self.fetch_rates(target_date)
        return sorted(rates.keys())


def get_cnb_rates(cache_dir: str = "data/cache") -> CNBExchangeRates:
    """
    Convenience function to get CNB rates instance.

    Args:
        cache_dir: Directory for caching rates

    Returns:
        CNBExchangeRates instance
    """
    return CNBExchangeRates(cache_dir)
