"""Dashboard API endpoints"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import date
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.repositories.transaction_repo import TransactionRepository
from backend.database.models import Owner

router = APIRouter()


@router.get("/dashboard/summary")
async def get_summary(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    owner: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get dashboard summary statistics from SQLite database"""
    try:
        repo = TransactionRepository(db)

        # Convert owner name to ID if provided
        owner_id = None
        if owner:
            owner_obj = db.query(Owner).filter(Owner.name == owner).first()
            owner_id = owner_obj.id if owner_obj else None

        # Get summary from repository
        summary = repo.get_summary(
            from_date=from_date,
            to_date=to_date,
            owner_id=owner_id
        )

        return {
            "period": {
                "from": from_date.isoformat() if from_date else None,
                "to": to_date.isoformat() if to_date else None
            },
            "totals": {
                "income": summary.get("income", 0.0),
                "expenses": abs(summary.get("expenses", 0.0)),  # Make positive for display
                "net": summary.get("net", 0.0),
                "transaction_count": summary.get("transaction_count", 0)
            },
            "internal_transfers": {
                "count": summary.get("internal_transfers", 0),
                "total": 0.0  # Internal transfers net to zero
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
