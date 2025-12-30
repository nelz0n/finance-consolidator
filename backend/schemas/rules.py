"""Pydantic schemas for categorization rules"""
from pydantic import BaseModel
from typing import Optional


class RuleBase(BaseModel):
    """Base rule schema"""
    priority: int = 0
    description_contains: Optional[str] = None
    institution_exact: Optional[str] = None
    counterparty_account_exact: Optional[str] = None
    counterparty_name_contains: Optional[str] = None
    variable_symbol_exact: Optional[str] = None
    type_contains: Optional[str] = None
    amount_czk_min: Optional[float] = None
    amount_czk_max: Optional[float] = None
    tier1: str
    tier2: str
    tier3: str
    owner: Optional[str] = None


class RuleCreate(RuleBase):
    """Schema for creating a new rule"""
    pass


class RuleUpdate(RuleBase):
    """Schema for updating a rule"""
    pass


class CategorizationRule(RuleBase):
    """Schema for categorization rule with ID"""
    id: int

    class Config:
        from_attributes = True
