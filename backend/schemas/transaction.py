"""Pydantic schemas for Transaction API"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from decimal import Decimal


class TransactionBase(BaseModel):
    """Base transaction schema"""
    date: datetime
    description: str
    amount: Decimal
    currency: str
    amount_czk: Optional[Decimal] = None
    exchange_rate: Optional[Decimal] = None
    category_tier1: Optional[str] = None
    category_tier2: Optional[str] = None
    category_tier3: Optional[str] = None
    is_internal_transfer: bool = False
    categorization_source: Optional[str] = None
    ai_confidence: Optional[int] = None


class TransactionCreate(TransactionBase):
    """Schema for creating a transaction"""
    transaction_id: str
    account_id: Optional[int] = None
    institution_id: Optional[int] = None
    owner_id: Optional[int] = None


class TransactionUpdate(BaseModel):
    """Schema for updating a transaction"""
    category_tier1: Optional[str] = None
    category_tier2: Optional[str] = None
    category_tier3: Optional[str] = None
    is_internal_transfer: Optional[bool] = None
    note: Optional[str] = None
    owner_id: Optional[int] = None


class TransactionResponse(TransactionBase):
    """Schema for transaction response"""
    id: int
    transaction_id: str
    account_id: Optional[int]
    institution_id: Optional[int]
    owner_id: Optional[int]
    transaction_type: Optional[str]
    counterparty_account: Optional[str]
    counterparty_name: Optional[str]
    source_file: Optional[str]
    processed_date: datetime
    synced_to_sheets: bool

    class Config:
        from_attributes = True


class TransactionFilter(BaseModel):
    """Schema for filtering transactions"""
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    owner_id: Optional[int] = None
    institution_id: Optional[int] = None
    account_id: Optional[int] = None
    category_tier1: Optional[str] = None
    category_tier2: Optional[str] = None
    category_tier3: Optional[str] = None
    is_internal_transfer: Optional[bool] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    search: Optional[str] = None
    page: int = Field(1, gt=0)
    per_page: int = Field(50, gt=0, le=200)
    sort_by: str = "date"
    sort_order: str = "desc"


class PaginatedTransactionResponse(BaseModel):
    """Paginated transaction response"""
    data: list[TransactionResponse]
    pagination: dict


class DashboardSummary(BaseModel):
    """Dashboard summary response"""
    period: dict
    totals: dict
    by_currency: Optional[dict] = None
    internal_transfers: dict
