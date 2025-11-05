"""Currency conversion utilities."""

from decimal import Decimal
from typing import Dict, Optional
from datetime import date
from src.utils.logger import get_logger

logger = get_logger()


class CurrencyConverter:
    """Handle currency conversions with optional CNB API integration."""

    def __init__(self, rates: Optional[Dict[str, float]] = None,
                 base_currency: str = "CZK",
                 use_cnb_api: bool = False,
                 cnb_cache_dir: str = "data/cache"):
        """
        Initialize converter with exchange rates.

        Args:
            rates: Dict of currency codes to exchange rates (vs base currency).
                   If None and use_cnb_api=True, will fetch from CNB.
            base_currency: Base currency for normalization (default: CZK)
            use_cnb_api: If True, fetch real-time rates from CNB API
            cnb_cache_dir: Directory for caching CNB rates
        """
        self.base_currency = base_currency
        self.use_cnb_api = use_cnb_api
        self.cnb_api = None

        # Initialize rates
        if rates:
            self.rates = {k: Decimal(str(v)) for k, v in rates.items()}
        else:
            self.rates = {}

        # Ensure base currency is in rates
        if base_currency not in self.rates:
            self.rates[base_currency] = Decimal("1.0")

        # Initialize CNB API if enabled
        if use_cnb_api:
            try:
                from src.utils.cnb_api import CNBExchangeRates
                self.cnb_api = CNBExchangeRates(cache_dir=cnb_cache_dir)
                logger.info("CNB API integration enabled for real-time exchange rates")
            except Exception as e:
                logger.error(f"Failed to initialize CNB API: {e}")
                logger.warning("Falling back to static rates")
                self.use_cnb_api = False
    
    def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: Optional[str] = None,
        transaction_date: Optional[date] = None
    ) -> Decimal:
        """
        Convert amount from one currency to another.

        Args:
            amount: Amount to convert
            from_currency: Source currency code
            to_currency: Target currency code (defaults to base currency)
            transaction_date: Date for exchange rate (used with CNB API)

        Returns:
            Converted amount
        """
        if to_currency is None:
            to_currency = self.base_currency

        # If same currency, no conversion needed
        if from_currency == to_currency:
            return amount

        # Use CNB API if enabled and base currency is CZK
        if self.use_cnb_api and self.cnb_api and self.base_currency == 'CZK':
            try:
                # Convert to CZK first
                if from_currency != 'CZK':
                    amount_czk = self.cnb_api.convert_to_czk(
                        amount, from_currency, transaction_date
                    )
                else:
                    amount_czk = amount

                # Then convert from CZK to target
                if to_currency != 'CZK':
                    result = self.cnb_api.convert_from_czk(
                        amount_czk, to_currency, transaction_date
                    )
                else:
                    result = amount_czk

                logger.debug(f"Converted {amount} {from_currency} to {result} {to_currency} using CNB rates")
                return result.quantize(Decimal('0.01'))

            except Exception as e:
                logger.warning(f"CNB API conversion failed: {e}, falling back to static rates")
                # Fall through to static rates

        # Fall back to static rates
        if from_currency not in self.rates:
            logger.warning(f"Currency {from_currency} not in rates, assuming 1:1 with {self.base_currency}")
            from_rate = Decimal("1.0")
        else:
            from_rate = self.rates[from_currency]

        if to_currency not in self.rates:
            logger.warning(f"Currency {to_currency} not in rates, assuming 1:1 with {self.base_currency}")
            to_rate = Decimal("1.0")
        else:
            to_rate = self.rates[to_currency]

        # Convert through base currency
        # amount_in_base = amount / from_rate
        # amount_in_target = amount_in_base * to_rate
        amount_in_base = amount / from_rate
        result = amount_in_base * to_rate

        logger.debug(f"Converted {amount} {from_currency} to {result} {to_currency}")
        return result.quantize(Decimal('0.01'))
    
    def get_rate(self, currency: str) -> Decimal:
        """Get exchange rate for a currency."""
        return self.rates.get(currency, Decimal("1.0"))
    
    def add_rate(self, currency: str, rate: float):
        """Add or update exchange rate."""
        self.rates[currency] = Decimal(str(rate))
        logger.info(f"Added/updated rate for {currency}: {rate}")


def normalize_currency_code(code: str) -> str:
    """Normalize currency code to standard format."""
    if not code:
        return "EUR"  # Default
    
    code = code.strip().upper()
    
    # Handle common variations
    mapping = {
        "CZK": "CZK",
        "KORUNA": "CZK",
        "KC": "CZK",
        "EUR": "EUR",
        "EURO": "EUR",
        "€": "EUR",
        "USD": "USD",
        "DOLLAR": "USD",
        "$": "USD",
    }
    
    return mapping.get(code, code)
