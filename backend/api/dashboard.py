"""Dashboard API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from datetime import date
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.repositories.transaction_repo import TransactionRepository
from backend.database.models import Owner
from backend.schemas.dashboard import (
    CategoryAggregation,
    MonthlyTrend,
    TopCounterparty,
    SavingsRateData,
    ComparisonResponse
)
from backend.utils.cache import cached, clear_dashboard_cache

router = APIRouter()


@router.get("/dashboard/summary")
@cached(ttl_seconds=300)  # 5-minute cache
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


@router.get("/dashboard/categories", response_model=List[CategoryAggregation])
@cached(ttl_seconds=300)  # 5-minute cache
async def get_category_breakdown(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    owner: Optional[str] = None,
    tier1: Optional[str] = None,
    tier2: Optional[str] = None,
    include_internal: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get hierarchical category breakdown with drill-down support.

    - No tier1/tier2: Returns tier1 breakdown
    - tier1 set: Returns tier2 breakdown under that tier1
    - tier1+tier2 set: Returns tier3 breakdown under that tier1+tier2
    """
    try:
        repo = TransactionRepository(db)

        # Convert owner name to ID
        owner_id = None
        if owner:
            owner_obj = db.query(Owner).filter(Owner.name == owner).first()
            owner_id = owner_obj.id if owner_obj else None

        results = repo.get_category_aggregations(
            from_date=from_date,
            to_date=to_date,
            owner_id=owner_id,
            tier1=tier1,
            tier2=tier2,
            include_internal=include_internal
        )

        return results
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/trends/monthly", response_model=List[MonthlyTrend])
@cached(ttl_seconds=300)  # 5-minute cache
async def get_monthly_trends(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    owner: Optional[str] = None,
    category_tier1: Optional[str] = None,
    include_internal: bool = False,
    db: Session = Depends(get_db)
):
    """Get monthly income/expense trends for time-series analysis"""
    try:
        repo = TransactionRepository(db)

        # Convert owner name to ID
        owner_id = None
        if owner:
            owner_obj = db.query(Owner).filter(Owner.name == owner).first()
            owner_id = owner_obj.id if owner_obj else None

        results = repo.get_monthly_time_series(
            from_date=from_date,
            to_date=to_date,
            owner_id=owner_id,
            category_tier1=category_tier1,
            include_internal=include_internal
        )

        return results
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/top-counterparties", response_model=List[TopCounterparty])
@cached(ttl_seconds=300)  # 5-minute cache
async def get_top_counterparties(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    owner: Optional[str] = None,
    type: str = Query('expense', pattern='^(expense|income)$'),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get top merchants/counterparties by spending or income"""
    try:
        repo = TransactionRepository(db)

        # Convert owner name to ID
        owner_id = None
        if owner:
            owner_obj = db.query(Owner).filter(Owner.name == owner).first()
            owner_id = owner_obj.id if owner_obj else None

        results = repo.get_top_counterparties(
            from_date=from_date,
            to_date=to_date,
            owner_id=owner_id,
            transaction_type=type,
            limit=limit
        )

        return results
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/savings-rate", response_model=List[SavingsRateData])
@cached(ttl_seconds=300)  # 5-minute cache
async def get_savings_rate(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    owner: Optional[str] = None,
    group_by: str = Query('month', pattern='^(month|quarter)$'),
    db: Session = Depends(get_db)
):
    """Get savings rate over time (monthly or quarterly)"""
    try:
        repo = TransactionRepository(db)

        # Convert owner name to ID
        owner_id = None
        if owner:
            owner_obj = db.query(Owner).filter(Owner.name == owner).first()
            owner_id = owner_obj.id if owner_obj else None

        results = repo.get_savings_rate_data(
            from_date=from_date,
            to_date=to_date,
            owner_id=owner_id,
            group_by=group_by
        )

        return results
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/comparison", response_model=ComparisonResponse)
@cached(ttl_seconds=300)  # 5-minute cache
async def get_period_comparison(
    current_start: date = Query(..., description="Start date of current period"),
    current_end: date = Query(..., description="End date of current period"),
    previous_start: date = Query(..., description="Start date of previous period"),
    previous_end: date = Query(..., description="End date of previous period"),
    owner: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Compare two time periods (month-over-month, year-over-year, custom)"""
    try:
        repo = TransactionRepository(db)

        # Convert owner name to ID
        owner_id = None
        if owner:
            owner_obj = db.query(Owner).filter(Owner.name == owner).first()
            owner_id = owner_obj.id if owner_obj else None

        result = repo.get_comparison_data(
            current_start=current_start,
            current_end=current_end,
            previous_start=previous_start,
            previous_end=previous_end,
            owner_id=owner_id
        )

        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/category-time-series")
async def get_category_time_series(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    owner: Optional[str] = None,
    include_internal: bool = False,
    db: Session = Depends(get_db)
):
    """Get category breakdown over time for stacked area chart"""
    try:
        repo = TransactionRepository(db)

        # Convert owner name to ID
        owner_id = None
        if owner:
            owner_obj = db.query(Owner).filter(Owner.name == owner).first()
            owner_id = owner_obj.id if owner_obj else None

        result = repo.get_category_time_series(
            from_date=from_date,
            to_date=to_date,
            owner_id=owner_id,
            include_internal=include_internal
        )

        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/test-endpoint")
async def test_endpoint_simple():
    """Simple test endpoint to verify router is working"""
    return {"status": "ok", "message": "Test endpoint is working!"}


@router.post("/dashboard/cache/clear")
async def clear_cache():
    """Clear dashboard cache (useful after uploading new transactions)"""
    try:
        clear_dashboard_cache()
        return {"message": "Dashboard cache cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
