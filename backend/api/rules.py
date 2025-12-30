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


def load_rules_from_sheets():
    """Load categorization rules from Google Sheets"""
    try:
        from src.utils.categorizer import TransactionCategorizer

        # Create categorizer instance to load rules
        categorizer = TransactionCategorizer(
            config_path="config/categorization.yaml",
            settings_path="config/settings.yaml",
            reload_rules=True  # Force reload from sheets
        )

        return categorizer.manual_rules
    except Exception as e:
        logger.error(f"Error loading rules from Google Sheets: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def save_rules_to_sheets(rules: List[Dict]):
    """Save categorization rules back to Google Sheets"""
    try:
        from src.connectors.google_sheets import GoogleSheetsConnector
        import yaml

        # Load settings
        with open("config/settings.yaml", 'r', encoding='utf-8') as f:
            settings = yaml.safe_load(f)

        cat_config = settings.get('categorization', {})
        sheets_config = cat_config.get('google_sheets', {})
        spreadsheet_id = sheets_config.get('spreadsheet_id',
                                          settings.get('google_sheets', {}).get('master_sheet_id'))
        rules_tab = sheets_config.get('rules_tab', 'Categorization_Rules')

        # Get credentials
        creds_path = settings.get('google_drive', {}).get('credentials_path')
        token_path = settings.get('google_drive', {}).get('token_path')

        # Connect to Google Sheets
        connector = GoogleSheetsConnector(creds_path, token_path)
        if not connector.authenticate():
            raise Exception("Failed to authenticate with Google Sheets")

        # Convert rules to rows format
        # Headers: Priority, Description_contains, Institution_exact, Counterparty_account_exact,
        #          Counterparty_name_contains, Variable_symbol_exact, Type_contains,
        #          Amount_czk_min, Amount_czk_max, Tier1, Tier2, Tier3, Owner
        rows = [[
            'Priority', 'Description_contains', 'Institution_exact', 'Counterparty_account_exact',
            'Counterparty_name_contains', 'Variable_symbol_exact', 'Type_contains',
            'Amount_czk_min', 'Amount_czk_max', 'Tier1', 'Tier2', 'Tier3', 'Owner'
        ]]

        for rule in rules:
            rows.append([
                rule.get('priority', 0),
                rule.get('description_contains', ''),
                rule.get('institution_exact', ''),
                rule.get('counterparty_account_exact', ''),
                rule.get('counterparty_name_contains', ''),
                rule.get('variable_symbol_exact', ''),
                rule.get('type_contains', ''),
                rule.get('amount_czk_min') if rule.get('amount_czk_min') is not None else '',
                rule.get('amount_czk_max') if rule.get('amount_czk_max') is not None else '',
                rule.get('tier1', ''),
                rule.get('tier2', ''),
                rule.get('tier3', ''),
                rule.get('owner', '')
            ])

        # Write to sheet (overwrites by default)
        connector.write_sheet(
            spreadsheet_id,
            f"{rules_tab}!A1",
            rows
        )

        return True
    except Exception as e:
        logger.error(f"Error saving rules to Google Sheets: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@router.get("", response_model=List[CategorizationRule])
async def list_rules():
    """Get all categorization rules"""
    try:
        rules = load_rules_from_sheets()

        # Convert to response model format
        formatted_rules = []
        for idx, rule in enumerate(rules):
            formatted_rules.append({
                'id': idx,
                'priority': rule.get('priority', 0),
                'description_contains': rule.get('description_contains', ''),
                'institution_exact': rule.get('institution_exact', ''),
                'counterparty_account_exact': rule.get('counterparty_account_exact', ''),
                'counterparty_name_contains': rule.get('counterparty_name_contains', ''),
                'variable_symbol_exact': rule.get('variable_symbol_exact', ''),
                'type_contains': rule.get('type_contains', ''),
                'amount_czk_min': rule.get('amount_czk_min'),
                'amount_czk_max': rule.get('amount_czk_max'),
                'tier1': rule.get('tier1', ''),
                'tier2': rule.get('tier2', ''),
                'tier3': rule.get('tier3', ''),
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
        rules = load_rules_from_sheets()

        # Create new rule dict
        new_rule = {
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
            'tier3': rule.tier3,
            'owner': rule.owner or ''
        }

        # Add to rules list
        rules.append(new_rule)

        # Sort by priority (higher first)
        rules.sort(key=lambda r: r.get('priority', 0), reverse=True)

        # Save back to sheets
        save_rules_to_sheets(rules)

        # Return created rule with ID
        new_rule['id'] = len(rules) - 1
        return new_rule
    except Exception as e:
        logger.error(f"Error creating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{rule_id}", response_model=CategorizationRule)
async def update_rule(rule_id: int, rule: RuleUpdate):
    """Update an existing categorization rule"""
    try:
        rules = load_rules_from_sheets()

        if rule_id < 0 or rule_id >= len(rules):
            raise HTTPException(status_code=404, detail="Rule not found")

        # Update rule
        updated_rule = {
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
            'tier3': rule.tier3,
            'owner': rule.owner or ''
        }

        rules[rule_id] = updated_rule

        # Sort by priority (higher first)
        rules.sort(key=lambda r: r.get('priority', 0), reverse=True)

        # Save back to sheets
        save_rules_to_sheets(rules)

        updated_rule['id'] = rule_id
        return updated_rule
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{rule_id}")
async def delete_rule(rule_id: int):
    """Delete a categorization rule"""
    try:
        rules = load_rules_from_sheets()

        if rule_id < 0 or rule_id >= len(rules):
            raise HTTPException(status_code=404, detail="Rule not found")

        # Remove rule
        deleted_rule = rules.pop(rule_id)

        # Save back to sheets
        save_rules_to_sheets(rules)

        return {'message': 'Rule deleted successfully', 'deleted': deleted_rule}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_rule(rule: RuleCreate, transaction: Dict):
    """Test a rule against a sample transaction"""
    try:
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
    except Exception as e:
        logger.error(f"Error testing rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))
