"""Balance/Position data model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from decimal import Decimal


@dataclass
class Balance:
    """Represents account balance or investment position."""
    
    # Core fields
    date: datetime
    account: str
    institution: str
    owner: str
    
    # Asset information
    asset_type: str  # "Cash", "Stock", "Bond", "Fund", etc.
    asset_name: Optional[str] = None  # Ticker symbol or asset name
    
    # Quantity and value
    quantity: Optional[Decimal] = None  # Number of units
    price: Optional[Decimal] = None  # Price per unit
    value: Decimal = Decimal(0)  # Total value in original currency
    currency: str = "EUR"
    
    # Normalized value
    value_eur: Optional[Decimal] = None
    
    # Metadata
    source_file: Optional[str] = None
    balance_id: Optional[str] = None
    processed_date: datetime = field(default_factory=datetime.now)
    
    # Additional details
    exchange_rate: Optional[Decimal] = None
    note: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for export."""
        return {
            'balance_id': self.balance_id,
            'date': self.date.strftime('%Y-%m-%d') if self.date else None,
            'account': self.account,
            'institution': self.institution,
            'owner': self.owner,
            'asset_type': self.asset_type,
            'asset_name': self.asset_name,
            'quantity': float(self.quantity) if self.quantity else None,
            'price': float(self.price) if self.price else None,
            'value': float(self.value) if self.value else None,
            'currency': self.currency,
            'value_eur': float(self.value_eur) if self.value_eur else None,
            'exchange_rate': float(self.exchange_rate) if self.exchange_rate else None,
            'note': self.note,
            'source_file': self.source_file,
            'processed_date': self.processed_date.strftime('%Y-%m-%d %H:%M:%S') if self.processed_date else None,
        }
    
    @classmethod
    def get_header(cls) -> list:
        """Get column headers for export."""
        return [
            'balance_id',
            'date',
            'account',
            'institution',
            'owner',
            'asset_type',
            'asset_name',
            'quantity',
            'price',
            'value',
            'currency',
            'value_eur',
            'exchange_rate',
            'note',
            'source_file',
            'processed_date',
        ]
