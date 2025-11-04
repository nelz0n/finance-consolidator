"""Transaction data model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from decimal import Decimal


@dataclass
class Transaction:
    """Represents a financial transaction."""
    
    # Core fields
    date: datetime
    description: str
    amount: Decimal
    currency: str
    
    # Normalized amount
    amount_eur: Optional[Decimal] = None
    
    # Classification
    category: Optional[str] = None
    account: Optional[str] = None
    institution: Optional[str] = None
    owner: Optional[str] = None
    transaction_type: Optional[str] = None
    
    # Metadata
    source_file: Optional[str] = None
    transaction_id: Optional[str] = None
    processed_date: datetime = field(default_factory=datetime.now)
    
    # Additional details (optional)
    counterparty_account: Optional[str] = None
    counterparty_name: Optional[str] = None
    counterparty_bank: Optional[str] = None
    reference: Optional[str] = None
    variable_symbol: Optional[str] = None
    constant_symbol: Optional[str] = None
    specific_symbol: Optional[str] = None
    note: Optional[str] = None
    exchange_rate: Optional[Decimal] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for export."""
        return {
            'transaction_id': self.transaction_id,
            'date': self.date.strftime('%Y-%m-%d') if self.date else None,
            'description': self.description,
            'amount': float(self.amount) if self.amount else None,
            'currency': self.currency,
            'amount_eur': float(self.amount_eur) if self.amount_eur else None,
            'category': self.category,
            'account': self.account,
            'institution': self.institution,
            'owner': self.owner,
            'type': self.transaction_type,
            'counterparty_account': self.counterparty_account,
            'counterparty_name': self.counterparty_name,
            'counterparty_bank': self.counterparty_bank,
            'reference': self.reference,
            'variable_symbol': self.variable_symbol,
            'constant_symbol': self.constant_symbol,
            'specific_symbol': self.specific_symbol,
            'note': self.note,
            'exchange_rate': float(self.exchange_rate) if self.exchange_rate else None,
            'source_file': self.source_file,
            'processed_date': self.processed_date.strftime('%Y-%m-%d %H:%M:%S') if self.processed_date else None,
        }
    
    @classmethod
    def get_header(cls) -> list:
        """Get column headers for export."""
        return [
            'transaction_id',
            'date',
            'description',
            'amount',
            'currency',
            'amount_eur',
            'category',
            'account',
            'institution',
            'owner',
            'type',
            'counterparty_account',
            'counterparty_name',
            'counterparty_bank',
            'reference',
            'variable_symbol',
            'constant_symbol',
            'specific_symbol',
            'note',
            'exchange_rate',
            'source_file',
            'processed_date',
        ]
