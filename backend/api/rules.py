"""Categorization Rules Management API"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
import logging
import yaml
from pathlib import Path

from backend.schemas.rules import (
    CategorizationRule,
    RuleCreate,
    RuleUpdate
)

logger = logging.getLogger(__name__)

router = APIRouter()


def load_rules_from_database():
    """Load categorization rules from SQLite database"""
    try:
        from backend.database.connection import get_db_context
        from backend.database.models import CategorizationRule
        import json

        with get_db_context() as db:
            # Get all active rules
            db_rules = db.query(CategorizationRule).filter(
                CategorizationRule.is_active == True
            ).order_by(CategorizationRule.priority.desc()).all()

            rules = []
            for rule in db_rules:
                # Parse JSON conditions
                conditions = json.loads(rule.conditions) if rule.conditions else {}

                rule_dict = {
                    'id': rule.id,
                    'name': rule.name,
                    'priority': rule.priority or 0,
                    'description': rule.description,
                    'category_tier1': rule.category_tier1,
                    'category_tier2': rule.category_tier2,
                    'category_tier3': rule.category_tier3,
                    'is_internal_transfer': rule.mark_as_internal,
                    'is_active': rule.is_active,
                    **conditions  # Merge conditions into rule dict
                }
                rules.append(rule_dict)

            logger.info(f"Loaded {len(rules)} rules from database")
            return rules

    except Exception as e:
        logger.error(f"Error loading rules from database: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


@router.get("", response_model=List[CategorizationRule])
async def list_rules():
    """Get all categorization rules"""
    try:
        rules = load_rules_from_database()

        # Convert to response model format
        formatted_rules = []
        for rule in rules:
            formatted_rules.append({
                'id': rule.get('id'),  # Use actual database ID, not array index
                'priority': rule.get('priority', 0),
                'description_contains': rule.get('description_contains', ''),
                'institution_exact': rule.get('institution_exact', ''),
                'counterparty_account_exact': rule.get('counterparty_account_exact', ''),
                'counterparty_name_contains': rule.get('counterparty_name_contains', ''),
                'variable_symbol_exact': rule.get('variable_symbol_exact', ''),
                'type_contains': rule.get('type_contains', ''),
                'amount_czk_min': rule.get('amount_czk_min'),
                'amount_czk_max': rule.get('amount_czk_max'),
                'tier1': rule.get('category_tier1', ''),
                'tier2': rule.get('category_tier2', ''),
                'tier3': rule.get('category_tier3', ''),
                'owner': rule.get('owner', '')
            })

        return formatted_rules
    except Exception as e:
        logger.error(f"Error fetching rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=CategorizationRule)
async def create_rule(rule: RuleCreate):
    """Create a new categorization rule"""
    try:
        from backend.database.connection import get_db_context
        from backend.database.models import CategorizationRule as DBRule
        import json

        # Build conditions JSON
        conditions = {}
        if rule.description_contains:
            conditions['description_contains'] = rule.description_contains
        if rule.institution_exact:
            conditions['institution_exact'] = rule.institution_exact
        if rule.counterparty_account_exact:
            conditions['counterparty_account_exact'] = rule.counterparty_account_exact
        if rule.counterparty_name_contains:
            conditions['counterparty_name_contains'] = rule.counterparty_name_contains
        if rule.variable_symbol_exact:
            conditions['variable_symbol_exact'] = rule.variable_symbol_exact
        if rule.type_contains:
            conditions['type_contains'] = rule.type_contains
        if rule.amount_czk_min is not None:
            conditions['amount_czk_min'] = float(rule.amount_czk_min)
        if rule.amount_czk_max is not None:
            conditions['amount_czk_max'] = float(rule.amount_czk_max)

        # Create database rule
        with get_db_context() as db:
            db_rule = DBRule(
                name=f"Rule_{rule.tier1}_{rule.tier2}_{rule.tier3}",
                description=rule.description_contains or f"Auto-categorize to {rule.tier1}/{rule.tier2}/{rule.tier3}",
                priority=rule.priority,
                is_active=True,
                conditions=json.dumps(conditions),
                category_tier1=rule.tier1,
                category_tier2=rule.tier2,
                category_tier3=rule.tier3,
                mark_as_internal=False
            )
            db.add(db_rule)
            db.commit()
            db.refresh(db_rule)

            # Return formatted rule
            return {
                'id': db_rule.id,
                'priority': db_rule.priority,
                'description_contains': rule.description_contains or '',
                'institution_exact': rule.institution_exact or '',
                'counterparty_account_exact': rule.counterparty_account_exact or '',
                'counterparty_name_contains': rule.counterparty_name_contains or '',
                'variable_symbol_exact': rule.variable_symbol_exact or '',
                'type_contains': rule.type_contains or '',
                'amount_czk_min': rule.amount_czk_min,
                'amount_czk_max': rule.amount_czk_max,
                'tier1': rule.tier1,
                'tier2': rule.tier2,
                'tier3': rule.tier3,
                'owner': rule.owner or ''
            }
    except Exception as e:
        logger.error(f"Error creating rule: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{rule_id}", response_model=CategorizationRule)
async def update_rule(rule_id: int, rule: RuleUpdate):
    """Update an existing categorization rule"""
    try:
        from backend.database.connection import get_db_context
        from backend.database.models import CategorizationRule as DBRule
        import json

        with get_db_context() as db:
            # Find existing rule
            db_rule = db.query(DBRule).filter(DBRule.id == rule_id).first()
            if not db_rule:
                raise HTTPException(status_code=404, detail="Rule not found")

            # Build conditions JSON
            conditions = {}
            if rule.description_contains:
                conditions['description_contains'] = rule.description_contains
            if rule.institution_exact:
                conditions['institution_exact'] = rule.institution_exact
            if rule.counterparty_account_exact:
                conditions['counterparty_account_exact'] = rule.counterparty_account_exact
            if rule.counterparty_name_contains:
                conditions['counterparty_name_contains'] = rule.counterparty_name_contains
            if rule.variable_symbol_exact:
                conditions['variable_symbol_exact'] = rule.variable_symbol_exact
            if rule.type_contains:
                conditions['type_contains'] = rule.type_contains
            if rule.amount_czk_min is not None:
                conditions['amount_czk_min'] = float(rule.amount_czk_min)
            if rule.amount_czk_max is not None:
                conditions['amount_czk_max'] = float(rule.amount_czk_max)

            # Update rule fields
            db_rule.name = f"Rule_{rule.tier1}_{rule.tier2}_{rule.tier3}"
            db_rule.description = rule.description_contains or f"Auto-categorize to {rule.tier1}/{rule.tier2}/{rule.tier3}"
            db_rule.priority = rule.priority
            db_rule.conditions = json.dumps(conditions)
            db_rule.category_tier1 = rule.tier1
            db_rule.category_tier2 = rule.tier2
            db_rule.category_tier3 = rule.tier3

            db.commit()
            db.refresh(db_rule)

            # Return formatted rule
            return {
                'id': db_rule.id,
                'priority': db_rule.priority,
                'description_contains': rule.description_contains or '',
                'institution_exact': rule.institution_exact or '',
                'counterparty_account_exact': rule.counterparty_account_exact or '',
                'counterparty_name_contains': rule.counterparty_name_contains or '',
                'variable_symbol_exact': rule.variable_symbol_exact or '',
                'type_contains': rule.type_contains or '',
                'amount_czk_min': rule.amount_czk_min,
                'amount_czk_max': rule.amount_czk_max,
                'tier1': rule.tier1,
                'tier2': rule.tier2,
                'tier3': rule.tier3,
                'owner': rule.owner or ''
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating rule: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{rule_id}")
async def delete_rule(rule_id: int):
    """Delete a categorization rule"""
    try:
        from backend.database.connection import get_db_context
        from backend.database.models import CategorizationRule as DBRule

        with get_db_context() as db:
            # Find and delete rule
            db_rule = db.query(DBRule).filter(DBRule.id == rule_id).first()
            if not db_rule:
                raise HTTPException(status_code=404, detail="Rule not found")

            rule_name = db_rule.name
            db.delete(db_rule)
            db.commit()

            return {'message': 'Rule deleted successfully', 'deleted': {'id': rule_id, 'name': rule_name}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting rule: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_rule(
    rule: RuleCreate,
    transaction: Optional[Dict] = None,
    count_matches: bool = False
):
    """
    Test a rule against a sample transaction or count matching transactions.

    Args:
        rule: The rule to test
        transaction: Optional transaction to test against (required if count_matches=False)
        count_matches: If True, count all transactions matching the rule conditions

    Returns:
        If count_matches=False: {'matches': bool, 'would_categorize_as': {...}}
        If count_matches=True: {'matching_count': int, 'rule_conditions': {...}}
    """
    try:
        if count_matches:
            # Count all transactions matching this rule
            from backend.database.connection import get_db_context
            from backend.database.repositories.transaction_repo import TransactionRepository

            # Build conditions dict from rule
            conditions = {}
            if rule.description_contains:
                conditions['description_contains'] = rule.description_contains
            if rule.institution_exact:
                conditions['institution_exact'] = rule.institution_exact
            if rule.counterparty_account_exact:
                conditions['counterparty_account_exact'] = rule.counterparty_account_exact
            if rule.counterparty_name_contains:
                conditions['counterparty_name_contains'] = rule.counterparty_name_contains
            if rule.variable_symbol_exact:
                conditions['variable_symbol_exact'] = rule.variable_symbol_exact
            if rule.type_contains:
                conditions['type_contains'] = rule.type_contains
            if rule.amount_czk_min is not None:
                conditions['amount_czk_min'] = rule.amount_czk_min
            if rule.amount_czk_max is not None:
                conditions['amount_czk_max'] = rule.amount_czk_max

            with get_db_context() as db:
                repo = TransactionRepository(db)
                matching_count = repo.count_rule_matches(conditions)

            return {
                'matching_count': matching_count,
                'rule_conditions': conditions,
                'would_categorize_as': {
                    'tier1': rule.tier1,
                    'tier2': rule.tier2,
                    'tier3': rule.tier3
                }
            }
        else:
            # Test against single transaction (original behavior)
            if transaction is None:
                raise HTTPException(
                    status_code=400,
                    detail="transaction parameter is required when count_matches=False"
                )

            from src.utils.categorizer import TransactionCategorizer

            categorizer = TransactionCategorizer(
                config_path="config/categorization.yaml",
                settings_path="config/settings.yaml"
            )

            # Convert rule to dict format
            rule_dict = {
                'priority': rule.priority,
                'description_contains': rule.description_contains or '',
                'institution_exact': rule.institution_exact or '',
                'counterparty_account_exact': rule.counterparty_account_exact or '',
                'counterparty_name_contains': rule.counterparty_name_contains or '',
                'variable_symbol_exact': rule.variable_symbol_exact or '',
                'type_contains': rule.type_contains or '',
                'amount_czk_min': rule.amount_czk_min,
                'amount_czk_max': rule.amount_czk_max,
                'tier1': rule.tier1,
                'tier2': rule.tier2,
                'tier3': rule.tier3
            }

            # Test if rule matches
            matches = categorizer._sheets_rule_matches(rule_dict, transaction)

            return {
                'matches': matches,
                'would_categorize_as': {
                    'tier1': rule.tier1,
                    'tier2': rule.tier2,
                    'tier3': rule.tier3
                } if matches else None
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing rule: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
