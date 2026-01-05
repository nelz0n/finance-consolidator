"""Transaction repository for database operations"""
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case

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

    def get_category_aggregations(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        owner_id: Optional[int] = None,
        tier1: Optional[str] = None,
        tier2: Optional[str] = None,
        include_internal: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get aggregated spending by category hierarchy with drill-down support.

        Args:
            from_date: Start date filter
            to_date: End date filter
            owner_id: Filter by owner
            tier1: When None, groups by tier1. When set, filters to this tier1 and groups by tier2
            tier2: When set with tier1, filters to tier1+tier2 and groups by tier3
            include_internal: Whether to include internal transfers

        Returns:
            List of category aggregations with income, expenses, net, count, percentage
        """
        # Determine which tier to group by based on drill-down level
        if tier1 is None:
            # Top level: group by tier1
            group_column = Transaction.category_tier1
        elif tier2 is None:
            # Second level: group by tier2 under specific tier1
            group_column = Transaction.category_tier2
        else:
            # Third level: group by tier3 under specific tier1+tier2
            group_column = Transaction.category_tier3

        # Build aggregation query
        query = self.db.query(
            group_column.label('category'),
            func.sum(
                func.coalesce(
                    case(
                        (Transaction.amount > 0, Transaction.amount_czk)
                    ),
                    0
                )
            ).label('income'),
            func.sum(
                func.coalesce(
                    case(
                        (Transaction.amount < 0, Transaction.amount_czk)
                    ),
                    0
                )
            ).label('expenses'),
            func.count(Transaction.id).label('count')
        )

        # Apply filters
        if from_date:
            query = query.filter(Transaction.date >= from_date)
        if to_date:
            query = query.filter(Transaction.date <= to_date)
        if owner_id:
            query = query.filter(Transaction.owner_id == owner_id)
        if not include_internal:
            query = query.filter(Transaction.is_internal_transfer == False)

        # Apply tier filters for drill-down
        if tier1:
            query = query.filter(Transaction.category_tier1 == tier1)
        if tier2:
            query = query.filter(Transaction.category_tier2 == tier2)

        # Group by category and order by expenses (descending)
        query = query.group_by(group_column)
        query = query.order_by(
            func.abs(
                func.sum(
                    func.coalesce(
                        case(
                            (Transaction.amount < 0, Transaction.amount_czk)
                        ),
                        0
                    )
                )
            ).desc()
        )

        results = query.all()

        # Calculate total expenses for percentage calculation
        total_expenses = sum(abs(float(r.expenses)) for r in results if r.expenses)

        # Format results
        output = []
        for row in results:
            if row.category:  # Skip null categories
                expenses_abs = abs(float(row.expenses)) if row.expenses else 0
                output.append({
                    'category': row.category,
                    'income': float(row.income) if row.income else 0,
                    'expenses': expenses_abs,
                    'net': float(row.income) + float(row.expenses) if row.income and row.expenses else 0,
                    'count': row.count,
                    'percentage': (expenses_abs / total_expenses * 100) if total_expenses > 0 else 0
                })

        return output

    def get_monthly_time_series(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        owner_id: Optional[int] = None,
        category_tier1: Optional[str] = None,
        include_internal: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get monthly aggregations for trend analysis.

        Returns monthly income, expenses, net, count, and savings rate.
        """
        # Use SQLAlchemy func.strftime to group by year-month
        month_label = func.strftime('%Y-%m', Transaction.date).label('month')

        query = self.db.query(
            month_label,
            func.sum(
                func.coalesce(
                    case(
                        (Transaction.amount > 0, Transaction.amount_czk)
                    ),
                    0
                )
            ).label('income'),
            func.sum(
                func.coalesce(
                    case(
                        (Transaction.amount < 0, Transaction.amount_czk)
                    ),
                    0
                )
            ).label('expenses'),
            func.count(Transaction.id).label('count')
        )

        # Apply filters
        if from_date:
            query = query.filter(Transaction.date >= from_date)
        if to_date:
            query = query.filter(Transaction.date <= to_date)
        if owner_id:
            query = query.filter(Transaction.owner_id == owner_id)
        if category_tier1:
            query = query.filter(Transaction.category_tier1 == category_tier1)
        if not include_internal:
            query = query.filter(Transaction.is_internal_transfer == False)

        # Group by month and order ascending (oldest first)
        query = query.group_by(month_label)
        query = query.order_by(month_label.asc())

        results = query.all()

        # Format results with savings rate calculation
        output = []
        for row in results:
            income = float(row.income) if row.income else 0
            expenses = float(row.expenses) if row.expenses else 0
            net = income + expenses
            savings_rate = (net / income * 100) if income > 0 else 0

            output.append({
                'month': row.month,
                'income': income,
                'expenses': abs(expenses),
                'net': net,
                'count': row.count,
                'savings_rate': round(savings_rate, 2)
            })

        return output

    def get_top_counterparties(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        owner_id: Optional[int] = None,
        transaction_type: str = 'expense',
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top merchants/counterparties by total amount.

        Args:
            transaction_type: 'expense' for top expenses, 'income' for top income sources
            limit: Number of top counterparties to return
        """
        # Build query
        query = self.db.query(
            Transaction.counterparty_name.label('counterparty'),
            func.sum(Transaction.amount_czk).label('total'),
            func.count(Transaction.id).label('count'),
            func.avg(Transaction.amount_czk).label('average')
        )

        # Apply filters
        if from_date:
            query = query.filter(Transaction.date >= from_date)
        if to_date:
            query = query.filter(Transaction.date <= to_date)
        if owner_id:
            query = query.filter(Transaction.owner_id == owner_id)

        # Filter by transaction type
        if transaction_type == 'expense':
            query = query.filter(Transaction.amount < 0)
        else:
            query = query.filter(Transaction.amount > 0)

        # Exclude internal transfers and null counterparties
        query = query.filter(Transaction.is_internal_transfer == False)
        query = query.filter(Transaction.counterparty_name.isnot(None))
        query = query.filter(Transaction.counterparty_name != '')

        # Group by counterparty
        query = query.group_by(Transaction.counterparty_name)

        # Order by total amount (descending by absolute value)
        query = query.order_by(func.abs(func.sum(Transaction.amount_czk)).desc())

        # Apply limit
        query = query.limit(limit)

        results = query.all()

        # Format results
        output = []
        for row in results:
            output.append({
                'counterparty': row.counterparty,
                'total': abs(float(row.total)) if row.total else 0,
                'count': row.count,
                'average': abs(float(row.average)) if row.average else 0
            })

        return output

    def get_savings_rate_data(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        owner_id: Optional[int] = None,
        group_by: str = 'month'
    ) -> List[Dict[str, Any]]:
        """
        Calculate savings rate over time.

        Savings Rate = (Income - Expenses) / Income * 100

        Args:
            group_by: 'month' or 'quarter' for grouping period
        """
        # Determine period grouping
        if group_by == 'quarter':
            # Quarter format: YYYY-Q1, YYYY-Q2, etc.
            period_label = func.strftime('%Y', Transaction.date).concat(
                '-Q' + ((func.cast(func.strftime('%m', Transaction.date), 'integer') - 1) / 3 + 1).cast('text')
            ).label('period')
        else:
            # Month format: YYYY-MM
            period_label = func.strftime('%Y-%m', Transaction.date).label('period')

        query = self.db.query(
            period_label,
            func.sum(
                func.coalesce(
                    case(
                        (Transaction.amount > 0, Transaction.amount_czk)
                    ),
                    0
                )
            ).label('income'),
            func.sum(
                func.coalesce(
                    case(
                        (Transaction.amount < 0, Transaction.amount_czk)
                    ),
                    0
                )
            ).label('expenses')
        )

        # Apply filters
        if from_date:
            query = query.filter(Transaction.date >= from_date)
        if to_date:
            query = query.filter(Transaction.date <= to_date)
        if owner_id:
            query = query.filter(Transaction.owner_id == owner_id)

        # Exclude internal transfers
        query = query.filter(Transaction.is_internal_transfer == False)

        # Group and order
        query = query.group_by(period_label)
        query = query.order_by(period_label.asc())

        results = query.all()

        # Calculate savings and rate
        output = []
        for row in results:
            income = float(row.income) if row.income else 0
            expenses = abs(float(row.expenses)) if row.expenses else 0
            savings = income - expenses
            rate = (savings / income * 100) if income > 0 else 0

            output.append({
                'period': row.period,
                'income': income,
                'expenses': expenses,
                'savings': savings,
                'rate': round(rate, 2)
            })

        return output

    def get_category_time_series(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        owner_id: Optional[int] = None,
        tier1: Optional[str] = None,
        tier2: Optional[str] = None,
        include_internal: bool = False
    ) -> Dict[str, Any]:
        """
        Get monthly breakdown by categories for stacked area chart.
        Supports drill-down: tier1 → tier2 → tier3

        Returns a dict with:
        - months: list of month labels
        - categories: list of category names
        - data: 2D array [category][month] of expense values
        """
        from sqlalchemy import func, case

        # Determine which tier to show based on drill-down state
        if tier1 and tier2:
            # Show tier3 breakdown for selected tier1+tier2
            category_field = Transaction.category_tier3
            categories_query = self.db.query(Transaction.category_tier3).distinct()
            categories_query = categories_query.filter(Transaction.category_tier1 == tier1)
            categories_query = categories_query.filter(Transaction.category_tier2 == tier2)
        elif tier1:
            # Show tier2 breakdown for selected tier1
            category_field = Transaction.category_tier2
            categories_query = self.db.query(Transaction.category_tier2).distinct()
            categories_query = categories_query.filter(Transaction.category_tier1 == tier1)
        else:
            # Show tier1 breakdown (top level)
            category_field = Transaction.category_tier1
            categories_query = self.db.query(Transaction.category_tier1).distinct()

        # Apply common filters
        if not include_internal:
            categories_query = categories_query.filter(Transaction.is_internal_transfer == False)
        categories_query = categories_query.filter(category_field.isnot(None))
        categories_query = categories_query.filter(Transaction.amount < 0)  # Only expenses

        if from_date:
            categories_query = categories_query.filter(Transaction.date >= from_date)
        if to_date:
            categories_query = categories_query.filter(Transaction.date <= to_date)
        if owner_id:
            categories_query = categories_query.filter(Transaction.owner_id == owner_id)

        all_categories = [row[0] for row in categories_query.all()]

        # Get monthly data for each category
        month_label = func.strftime('%Y-%m', Transaction.date).label('month')

        query = self.db.query(
            month_label,
            category_field,
            func.sum(func.abs(Transaction.amount_czk)).label('expenses')
        )

        # Apply filters
        if from_date:
            query = query.filter(Transaction.date >= from_date)
        if to_date:
            query = query.filter(Transaction.date <= to_date)
        if owner_id:
            query = query.filter(Transaction.owner_id == owner_id)
        if not include_internal:
            query = query.filter(Transaction.is_internal_transfer == False)

        # Apply drill-down filters
        if tier1:
            query = query.filter(Transaction.category_tier1 == tier1)
        if tier2:
            query = query.filter(Transaction.category_tier2 == tier2)

        query = query.filter(category_field.isnot(None))
        query = query.filter(Transaction.amount < 0)  # Only expenses

        query = query.group_by(month_label, category_field)
        query = query.order_by(month_label)

        results = query.all()

        # Organize data by month and category
        months_data = {}
        for row in results:
            month = row.month
            category = row[1]  # The category field (tier1, tier2, or tier3)
            expenses = float(row.expenses) if row.expenses else 0

            if month not in months_data:
                months_data[month] = {}
            months_data[month][category] = expenses

        # Get sorted list of months
        months = sorted(months_data.keys())

        # Build 2D data array: data[category][month_index]
        data = {}
        for category in all_categories:
            data[category] = []
            for month in months:
                value = months_data.get(month, {}).get(category, 0)
                data[category].append(value)

        return {
            'months': months,
            'categories': all_categories,
            'data': data
        }

    def get_comparison_data(
        self,
        current_start: date,
        current_end: date,
        previous_start: date,
        previous_end: date,
        owner_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Compare two time periods (month-over-month, year-over-year).

        Returns current vs previous period metrics with change calculations.
        """
        def get_period_metrics(start_date: date, end_date: date) -> Dict[str, float]:
            """Helper to get metrics for a specific period"""
            query = self.db.query(Transaction)

            query = query.filter(Transaction.date >= start_date)
            query = query.filter(Transaction.date <= end_date)

            if owner_id:
                query = query.filter(Transaction.owner_id == owner_id)

            query = query.filter(Transaction.is_internal_transfer == False)

            # Calculate aggregates
            income = query.filter(Transaction.amount > 0).with_entities(
                func.sum(Transaction.amount_czk)
            ).scalar() or 0

            expenses = query.filter(Transaction.amount < 0).with_entities(
                func.sum(Transaction.amount_czk)
            ).scalar() or 0

            count = query.count()

            return {
                'income': float(income),
                'expenses': abs(float(expenses)),
                'net': float(income) + float(expenses),
                'count': count
            }

        # Get metrics for both periods
        current = get_period_metrics(current_start, current_end)
        previous = get_period_metrics(previous_start, previous_end)

        # Calculate changes
        change = {
            'income': current['income'] - previous['income'],
            'expenses': current['expenses'] - previous['expenses'],
            'net': current['net'] - previous['net'],
            'count': current['count'] - previous['count']
        }

        # Calculate percentage changes (handle division by zero)
        change_percent = {}
        for key in ['income', 'expenses', 'net']:
            if previous[key] != 0:
                change_percent[key] = round((change[key] / previous[key]) * 100, 2)
            else:
                change_percent[key] = 0 if change[key] == 0 else 100

        if previous['count'] != 0:
            change_percent['count'] = round((change['count'] / previous['count']) * 100, 2)
        else:
            change_percent['count'] = 0 if change['count'] == 0 else 100

        return {
            'current': current,
            'previous': previous,
            'change': change,
            'change_percent': change_percent
        }
