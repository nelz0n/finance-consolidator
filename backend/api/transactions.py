"""Transactions API endpoints"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from datetime import date
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.repositories.transaction_repo import TransactionRepository
from backend.database.models import Owner, Institution

router = APIRouter()


@router.get("/transactions")
async def get_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    owner: Optional[str] = None,
    institution: Optional[str] = None,
    category_tier1: Optional[str] = None,
    category_tier2: Optional[str] = None,
    category_tier3: Optional[str] = None,
    is_internal_transfer: Optional[bool] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    search: Optional[str] = None,
    sort_by: str = Query("date"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db)
):
    """Get all transactions from SQLite database with filtering and pagination"""
    try:
        repo = TransactionRepository(db)

        # Convert owner/institution names to IDs if provided
        owner_id = None
        if owner:
            owner_obj = db.query(Owner).filter(Owner.name == owner).first()
            owner_id = owner_obj.id if owner_obj else None

        institution_id = None
        if institution:
            inst_obj = db.query(Institution).filter(Institution.name == institution).first()
            institution_id = inst_obj.id if inst_obj else None

        transactions, total = repo.get_all(
            skip=skip,
            limit=limit,
            from_date=from_date,
            to_date=to_date,
            owner_id=owner_id,
            institution_id=institution_id,
            category_tier1=category_tier1,
            category_tier2=category_tier2,
            category_tier3=category_tier3,
            is_internal_transfer=is_internal_transfer,
            min_amount=min_amount,
            max_amount=max_amount,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )

        total_pages = (total + limit - 1) // limit if limit > 0 else 0

        # Convert ORM objects to dicts for JSON serialization
        transaction_dicts = []
        for txn in transactions:
            txn_dict = {
                "id": txn.id,
                "transaction_id": txn.transaction_id,
                "date": txn.date.isoformat() if txn.date else None,
                "description": txn.description,
                "amount": float(txn.amount) if txn.amount else 0,
                "currency": txn.currency,
                "amount_czk": float(txn.amount_czk) if txn.amount_czk else 0,
                "exchange_rate": float(txn.exchange_rate) if txn.exchange_rate else None,
                "owner": txn.owner.name if txn.owner else None,
                "institution": txn.institution.name if txn.institution else None,
                "account_number": txn.account.account_number if txn.account else None,
                "category_tier1": txn.category_tier1,
                "category_tier2": txn.category_tier2,
                "category_tier3": txn.category_tier3,
                "counterparty_account": txn.counterparty_account,
                "counterparty_name": txn.counterparty_name,
                "counterparty_bank": txn.counterparty_bank,
                "is_internal_transfer": txn.is_internal_transfer,
                "categorization_source": txn.categorization_source,
                "ai_confidence": txn.ai_confidence,
                "variable_symbol": txn.variable_symbol,
                "constant_symbol": txn.constant_symbol,
                "specific_symbol": txn.specific_symbol,
                "transaction_type": txn.transaction_type,
                "note": txn.note
            }
            transaction_dicts.append(txn_dict)

        return {
            "data": transaction_dicts,
            "pagination": {
                "page": (skip // limit) + 1,
                "per_page": limit,
                "total_pages": total_pages,
                "total_items": total
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transactions/reapply-rules")
async def reapply_rules(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    owner: Optional[str] = None,
    institution: Optional[str] = None,
    category_tier1: Optional[str] = None,
    category_tier2: Optional[str] = None,
    category_tier3: Optional[str] = None,
    is_internal_transfer: Optional[bool] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Re-apply manual categorization rules to filtered transactions.

    Logic:
    - Try to match manual rules (AI disabled)
    - If manual rule matches → Update categories
    - If NO manual rule matches AND transaction was previously AI-categorized → Keep original AI categories
    - Otherwise → Leave as-is
    """
    try:
        from src.utils.categorizer import get_categorizer

        repo = TransactionRepository(db)

        # Convert owner/institution names to IDs if provided
        owner_id = None
        if owner:
            owner_obj = db.query(Owner).filter(Owner.name == owner).first()
            owner_id = owner_obj.id if owner_obj else None

        institution_id = None
        if institution:
            inst_obj = db.query(Institution).filter(Institution.name == institution).first()
            institution_id = inst_obj.id if inst_obj else None

        # Get filtered transactions (no pagination - get all matching)
        transactions, total = repo.get_all(
            skip=0,
            limit=10000,  # High limit to get all
            from_date=from_date,
            to_date=to_date,
            owner_id=owner_id,
            institution_id=institution_id,
            category_tier1=category_tier1,
            category_tier2=category_tier2,
            category_tier3=category_tier3,
            is_internal_transfer=is_internal_transfer,
            min_amount=min_amount,
            max_amount=max_amount,
            search=search,
            sort_by="date",
            sort_order="desc"
        )

        if not transactions:
            return {
                "status": "completed",
                "message": "No transactions match the filter",
                "stats": {
                    "total_checked": 0,
                    "updated_by_rule": 0,
                    "preserved_ai": 0,
                    "unchanged": 0
                }
            }

        # Get categorizer (with manual rules loaded)
        categorizer = get_categorizer()

        stats = {
            "total_checked": len(transactions),
            "updated_by_rule": 0,
            "preserved_ai": 0,
            "unchanged": 0
        }

        # Process each transaction
        for txn_obj in transactions:
            # Convert ORM object to dict for categorizer
            txn = {
                'date': txn_obj.date.isoformat() if txn_obj.date else None,
                'description': txn_obj.description,
                'amount': float(txn_obj.amount) if txn_obj.amount else 0,
                'currency': txn_obj.currency,
                'counterparty_account': txn_obj.counterparty_account,
                'counterparty_name': txn_obj.counterparty_name,
                'counterparty_bank': txn_obj.counterparty_bank,
                'variable_symbol': txn_obj.variable_symbol,
                'constant_symbol': txn_obj.constant_symbol,
                'specific_symbol': txn_obj.specific_symbol,
                'owner': txn_obj.owner.name if txn_obj.owner else None,
                'account_number': txn_obj.account.account_number if txn_obj.account else None
            }

            original_source = txn_obj.categorization_source or ''

            # Try to categorize with manual rules only (AI disabled)
            tier1, tier2, tier3, owner_new, is_internal, source, confidence = categorizer.categorize(
                txn,
                disable_ai=True
            )

            # Determine what to do
            if source == 'manual_rule':
                # Manual rule matched - update the transaction
                updates = {
                    'category_tier1': tier1,
                    'category_tier2': tier2,
                    'category_tier3': tier3,
                    'categorization_source': 'manual_rule',
                    'ai_confidence': None
                }

                # Update owner if determined by rule
                if owner_new and owner_new != 'Unknown':
                    owner_obj = db.query(Owner).filter(Owner.name == owner_new).first()
                    if owner_obj:
                        updates['owner_id'] = owner_obj.id

                repo.update(txn_obj.id, updates)
                stats["updated_by_rule"] += 1

            elif source == 'uncategorized' and original_source == 'ai':
                # No manual rule matched, but it was AI-categorized before
                # Keep the original AI categories (do nothing)
                stats["preserved_ai"] += 1

            else:
                # No manual rule matched, and it wasn't AI-categorized
                # Leave as-is (internal_transfer, old manual_rule, uncategorized)
                stats["unchanged"] += 1

        return {
            "status": "completed",
            "message": f"Re-applied rules to {total} transactions",
            "stats": stats
        }

    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error re-applying rules: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions/uncategorized/list")
async def get_uncategorized(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get uncategorized transactions"""
    try:
        repo = TransactionRepository(db)
        transactions = repo.get_uncategorized(limit=limit)

        # Convert to dicts
        transaction_dicts = []
        for txn in transactions:
            txn_dict = {
                "id": txn.id,
                "transaction_id": txn.transaction_id,
                "date": txn.date.isoformat() if txn.date else None,
                "description": txn.description,
                "amount": float(txn.amount) if txn.amount else 0,
                "currency": txn.currency,
                "owner": txn.owner.name if txn.owner else None,
                "institution": txn.institution.name if txn.institution else None,
                "category_tier1": txn.category_tier1,
                "category_tier2": txn.category_tier2,
                "category_tier3": txn.category_tier3
            }
            transaction_dicts.append(txn_dict)

        return {
            "transactions": transaction_dicts,
            "count": len(transaction_dicts)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions/{transaction_id}")
async def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db)
):
    """Get a single transaction by ID"""
    try:
        repo = TransactionRepository(db)
        transaction = repo.get_by_id(transaction_id)

        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        # Convert to dict
        txn_dict = {
            "id": transaction.id,
            "transaction_id": transaction.transaction_id,
            "date": transaction.date.isoformat() if transaction.date else None,
            "description": transaction.description,
            "amount": float(transaction.amount) if transaction.amount else 0,
            "currency": transaction.currency,
            "amount_czk": float(transaction.amount_czk) if transaction.amount_czk else 0,
            "exchange_rate": float(transaction.exchange_rate) if transaction.exchange_rate else None,
            "owner": transaction.owner.name if transaction.owner else None,
            "institution": transaction.institution.name if transaction.institution else None,
            "account_number": transaction.account.account_number if transaction.account else None,
            "category_tier1": transaction.category_tier1,
            "category_tier2": transaction.category_tier2,
            "category_tier3": transaction.category_tier3,
            "counterparty_account": transaction.counterparty_account,
            "counterparty_name": transaction.counterparty_name,
            "counterparty_bank": transaction.counterparty_bank,
            "is_internal_transfer": transaction.is_internal_transfer,
            "categorization_source": transaction.categorization_source,
            "ai_confidence": transaction.ai_confidence,
            "variable_symbol": transaction.variable_symbol,
            "constant_symbol": transaction.constant_symbol,
            "specific_symbol": transaction.specific_symbol,
            "transaction_type": transaction.transaction_type,
            "note": transaction.note
        }

        return txn_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/transactions/{transaction_id}")
async def update_transaction(
    transaction_id: int,
    updates: dict,
    db: Session = Depends(get_db)
):
    """Update a transaction in SQLite database"""
    try:
        repo = TransactionRepository(db)

        # Remove None values
        clean_updates = {k: v for k, v in updates.items() if v is not None}

        updated_txn = repo.update(transaction_id, clean_updates)

        if not updated_txn:
            raise HTTPException(status_code=404, detail="Transaction not found or update failed")

        return {"status": "updated", "transaction_id": transaction_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/transactions/{transaction_id}")
async def delete_transaction(transaction_id: int):
    """Delete a transaction from Google Sheets (not implemented - would require sheet manipulation)"""
    raise HTTPException(
        status_code=501,
        detail="Delete not supported with Google Sheets backend. Please use Google Sheets UI to delete rows."
    )
