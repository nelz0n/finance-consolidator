"""Pydantic schemas for categories"""
from pydantic import BaseModel
from typing import List, Optional


class Tier3Category(BaseModel):
    """Tier3 category (leaf node)"""
    name: str


class Tier2Category(BaseModel):
    """Tier2 category with tier3 children"""
    tier2: str
    tier3: List[str] = []

    class Config:
        from_attributes = True


class Tier1Category(BaseModel):
    """Tier1 category with tier2 children"""
    tier1: str
    tier2_categories: List[Tier2Category] = []

    class Config:
        from_attributes = True


class CategoryTree(BaseModel):
    """Complete category tree"""
    categories: List[Tier1Category]


class CategoryCreate(BaseModel):
    """Create new category"""
    name: str
    parent_tier1: Optional[str] = None
    parent_tier2: Optional[str] = None


class CategoryUpdate(BaseModel):
    """Update category"""
    new_name: str
