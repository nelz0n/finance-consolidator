"""Currency conversion utilities."""

from decimal import Decimal
from typing import Dict, Optional
from src.utils.logger import get_logger

logger = get_logger()


class CurrencyConverter:
    """Handle currency conversions."""
    
    def __init__(self, rates: Dict[str, float], base_currency: str = "EUR"):
        """
        Initialize converter with exchange rates.
        
        Args:
            rates: Dict of currency codes to exchange rates (vs base currency)
            base_currency: Base currency for normalization
        """
        self.rates = {k: Decimal(str(v)) for k, v in rates.items()}
        self.base_currency = base_currency
        
        # Ensure base currency is in rates
        if base_currency not in self.rates:
            self.rates[base_currency] = Decimal("1.0")
    
    def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: Optional[str] = None
    ) -> Decimal:
        """
        Convert amount from one currency to another.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency code
            to_currency: Target currency code (defaults to base currency)
            
        Returns:
            Converted amount
        """
        if to_currency is None:
            to_currency = self.base_currency
        
        # If same currency, no conversion needed
        if from_currency == to_currency:
            return amount
        
        # Check if currencies are supported
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
        return result
    
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
