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

    # Normalized amount (in CZK)
    amount_czk: Optional[Decimal] = None

    # 3-Tier Categorization
    category_tier1: Optional[str] = None  # High level (e.g., "Living Expenses")
    category_tier2: Optional[str] = None  # Medium level (e.g., "Groceries")
    category_tier3: Optional[str] = None  # Detailed level (e.g., "Supermarket")

    # Legacy category field (for backward compatibility)
    # Will be set to tier3 or concatenated version
    category: Optional[str] = None

    # Internal transfer flag
    is_internal_transfer: Optional[bool] = False

    # Categorization metadata
    categorization_source: Optional[str] = None  # "manual_rule", "ai", "internal_transfer", "uncategorized"
    ai_confidence: Optional[int] = None  # 0-100, only set if categorization_source == "ai"

    # Classification
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
            'amount_czk': float(self.amount_czk) if self.amount_czk else None,
            'exchange_rate': float(self.exchange_rate) if self.exchange_rate else None,
            'category_tier1': self.category_tier1,
            'category_tier2': self.category_tier2,
            'category_tier3': self.category_tier3,
            'is_internal_transfer': self.is_internal_transfer,
            'categorization_source': self.categorization_source,
            'ai_confidence': self.ai_confidence,
            'account': self.account,
            'institution': self.institution,
            'owner': self.owner,
            'type': self.transaction_type,
            'counterparty_account': self.counterparty_account,
            'counterparty_name': self.counterparty_name,
            'variable_symbol': self.variable_symbol,
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
            'amount_czk',
            'exchange_rate',
            'category_tier1',
            'category_tier2',
            'category_tier3',
            'is_internal_transfer',
            'categorization_source',
            'ai_confidence',
            'account',
            'institution',
            'owner',
            'type',
            'counterparty_account',
            'counterparty_name',
            'variable_symbol',
            'source_file',
            'processed_date',
        ]
