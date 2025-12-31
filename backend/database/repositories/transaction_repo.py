"""Transaction repository for database operations"""
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from backend.database.models import Transaction, Account, Institution, Owner


class TransactionRepository:
    """Repository for transaction database operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """Get transaction by ID"""
        return self.db.query(Transaction).filter(Transaction.id == transaction_id).first()

    def get_by_transaction_id(self, txn_id: str) -> Optional[Transaction]:
        """Get transaction by transaction_id (TXN_20241015_001)"""
        return self.db.query(Transaction).filter(Transaction.transaction_id == txn_id).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 50,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        owner_id: Optional[int] = None,
        institution_id: Optional[int] = None,
        account_id: Optional[int] = None,
        category_tier1: Optional[str] = None,
        category_tier2: Optional[str] = None,
        category_tier3: Optional[str] = None,
        is_internal_transfer: Optional[bool] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        search: Optional[str] = None,
        sort_by: str = "date",
        sort_order: str = "desc"
    ) -> tuple[List[Transaction], int]:
        """
        Get all transactions with filtering and pagination.

        Returns: (transactions, total_count)
        """
        query = self.db.query(Transaction)

        # Apply filters
        if from_date:
            query = query.filter(Transaction.date >= from_date)
        if to_date:
            query = query.filter(Transaction.date <= to_date)
        if owner_id:
            query = query.filter(Transaction.owner_id == owner_id)
        if institution_id:
            query = query.filter(Transaction.institution_id == institution_id)
        if account_id:
            query = query.filter(Transaction.account_id == account_id)
        if category_tier1:
            query = query.filter(Transaction.category_tier1 == category_tier1)
        if category_tier2:
            query = query.filter(Transaction.category_tier2 == category_tier2)
        if category_tier3:
            query = query.filter(Transaction.category_tier3 == category_tier3)
        if is_internal_transfer is not None:
            query = query.filter(Transaction.is_internal_transfer == is_internal_transfer)
        if min_amount is not None:
            query = query.filter(Transaction.amount >= min_amount)
        if max_amount is not None:
            query = query.filter(Transaction.amount <= max_amount)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Transaction.description.ilike(search_term),
                    Transaction.counterparty_name.ilike(search_term)
                )
            )

        # Get total count before pagination
        total_count = query.count()

        # Apply sorting
        if sort_order == "desc":
            query = query.order_by(getattr(Transaction, sort_by).desc())
        else:
            query = query.order_by(getattr(Transaction, sort_by).asc())

        # Apply pagination
        transactions = query.offset(skip).limit(limit).all()

        return transactions, total_count

    def create(self, transaction_data: Dict[str, Any]) -> Transaction:
        """Create a new transaction"""
        transaction = Transaction(**transaction_data)
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def update(self, transaction_id: int, update_data: Dict[str, Any]) -> Optional[Transaction]:
        """Update a transaction"""
        transaction = self.get_by_id(transaction_id)
        if not transaction:
            return None

        for key, value in update_data.items():
            setattr(transaction, key, value)

        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def bulk_update(self, transaction_ids: List[int], update_data: Dict[str, Any]) -> int:
        """Bulk update transactions. Returns count of updated records."""
        count = self.db.query(Transaction).filter(
            Transaction.id.in_(transaction_ids)
        ).update(update_data, synchronize_session=False)
        self.db.commit()
        return count

    def delete(self, transaction_id: int) -> bool:
        """Delete a transaction"""
        transaction = self.get_by_id(transaction_id)
        if not transaction:
            return False

        self.db.delete(transaction)
        self.db.commit()
        return True

    def get_summary(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        owner_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get summary statistics for dashboard"""
        query = self.db.query(Transaction)

        if from_date:
            query = query.filter(Transaction.date >= from_date)
        if to_date:
            query = query.filter(Transaction.date <= to_date)
        if owner_id:
            query = query.filter(Transaction.owner_id == owner_id)

        # Calculate totals
        total_income = query.filter(Transaction.amount > 0).with_entities(
            func.sum(Transaction.amount_czk)
        ).scalar() or 0

        total_expenses = query.filter(Transaction.amount < 0).with_entities(
            func.sum(Transaction.amount_czk)
        ).scalar() or 0

        transaction_count = query.count()

        internal_transfers = query.filter(
            Transaction.is_internal_transfer == True
        ).count()

        return {
            "income": float(total_income),
            "expenses": float(total_expenses),
            "net": float(total_income + total_expenses),
            "transaction_count": transaction_count,
            "internal_transfers": internal_transfers
        }

    def get_uncategorized(self, limit: int = 100) -> List[Transaction]:
        """Get uncategorized transactions"""
        return self.db.query(Transaction).filter(
            Transaction.categorization_source == "uncategorized"
        ).limit(limit).all()

    def mark_synced(self, transaction_ids: List[int]) -> int:
        """Mark transactions as synced to Google Sheets"""
        return self.bulk_update(
            transaction_ids,
            {"synced_to_sheets": True, "synced_at": datetime.utcnow()}
        )

    def get_unsynced(self) -> List[Transaction]:
        """Get transactions not yet synced to Google Sheets"""
        return self.db.query(Transaction).filter(
            Transaction.synced_to_sheets == False
        ).all()
