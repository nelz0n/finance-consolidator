"""
Migrate categorization rules and category tree from Google Sheets to SQLite database.

This script:
1. Reads rules from Google Sheets Categorization_Rules tab
2. Reads categories from Google Sheets Categories tab
3. Imports them into SQLite database

Run this script once to migrate existing rules and categories.
"""

import sys
import yaml
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.connection import get_db_context, init_db
from backend.database.models import CategorizationRule, Category
from src.connectors.google_sheets import GoogleSheetsConnector
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_settings():
    """Load settings from YAML."""
    with open("config/settings.yaml", 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def migrate_categories(sheets: GoogleSheetsConnector, spreadsheet_id: str):
    """Migrate categories from Google Sheets to database."""
    logger.info("=" * 60)
    logger.info("Migrating Categories from Google Sheets to SQLite")
    logger.info("=" * 60)

    # Read from Google Sheets
    data = sheets.read_sheet(spreadsheet_id, "Categories!A:C")

    if not data or len(data) < 2:
        logger.warning("No category data found in Google Sheets")
        return 0

    headers = data[0]
    rows = data[1:]

    # Expected columns: tier1, tier2, tier3
    tier1_idx = headers.index('tier1') if 'tier1' in headers else 0
    tier2_idx = headers.index('tier2') if 'tier2' in headers else 1
    tier3_idx = headers.index('tier3') if 'tier3' in headers else 2

    migrated_count = 0

    with get_db_context() as db:
        # Clear existing categories
        db.query(Category).delete()
        logger.info("Cleared existing categories from database")

        for row in rows:
            if len(row) < 1:
                continue

            tier1 = row[tier1_idx] if tier1_idx < len(row) else ""
            tier2 = row[tier2_idx] if tier2_idx < len(row) else None
            tier3 = row[tier3_idx] if tier3_idx < len(row) else None

            if not tier1:
                continue

            # Clean empty values
            if tier2 == "":
                tier2 = None
            if tier3 == "":
                tier3 = None

            # Check if already exists
            existing = db.query(Category).filter(
                Category.tier1 == tier1,
                Category.tier2 == tier2,
                Category.tier3 == tier3
            ).first()

            if not existing:
                category = Category(
                    tier1=tier1,
                    tier2=tier2,
                    tier3=tier3
                )
                db.add(category)
                migrated_count += 1

                if migrated_count % 20 == 0:
                    db.flush()

        db.commit()
        logger.info(f"✅ Migrated {migrated_count} categories to database")

    return migrated_count


def migrate_rules(sheets: GoogleSheetsConnector, spreadsheet_id: str):
    """Migrate categorization rules from Google Sheets to database."""
    logger.info("=" * 60)
    logger.info("Migrating Categorization Rules from Google Sheets to SQLite")
    logger.info("=" * 60)

    # Read from Google Sheets
    data = sheets.read_sheet(spreadsheet_id, "Categorization_Rules!A:M")

    if not data or len(data) < 2:
        logger.warning("No rules data found in Google Sheets")
        return 0

    headers = [h.lower().replace(' ', '_') for h in data[0]]
    rows = data[1:]

    logger.info(f"Headers: {headers}")

    migrated_count = 0

    with get_db_context() as db:
        # Clear existing rules
        db.query(CategorizationRule).delete()
        logger.info("Cleared existing rules from database")

        for idx, row in enumerate(rows, start=2):
            if len(row) < 1:
                continue

            # Parse row into dict
            rule_data = {}
            for i, header in enumerate(headers):
                value = row[i] if i < len(row) else ""
                if value == "":
                    value = None
                rule_data[header] = value

            # Skip if no tier1 category (must have at least this)
            if not rule_data.get('tier1'):
                continue

            # Build conditions JSON from column matchers
            conditions = {}

            # These are the matching columns from your schema
            if rule_data.get('description_contains'):
                conditions['description_contains'] = rule_data['description_contains']
            if rule_data.get('counterparty_name_contains'):
                conditions['counterparty_name_contains'] = rule_data['counterparty_name_contains']
            if rule_data.get('counterparty_account_exact'):
                conditions['counterparty_account'] = rule_data['counterparty_account_exact']
            if rule_data.get('variable_symbol_exact'):
                conditions['variable_symbol'] = rule_data['variable_symbol_exact']
            if rule_data.get('institution_exact'):
                conditions['institution'] = rule_data['institution_exact']
            if rule_data.get('type_contains'):
                conditions['type_contains'] = rule_data['type_contains']
            if rule_data.get('amount_czk_min'):
                conditions['amount_czk_min'] = rule_data['amount_czk_min']
            if rule_data.get('amount_czk_max'):
                conditions['amount_czk_max'] = rule_data['amount_czk_max']

            # Generate a name from the rule conditions
            name_parts = []
            if rule_data.get('description_contains'):
                name_parts.append(f"desc:{rule_data['description_contains'][:20]}")
            if rule_data.get('counterparty_name_contains'):
                name_parts.append(f"cpty:{rule_data['counterparty_name_contains'][:20]}")
            if rule_data.get('tier1'):
                name_parts.append(f"→{rule_data['tier1']}")

            rule_name = " ".join(name_parts) if name_parts else f"Rule_{idx}"

            # Handle owner (convert name to owner_id if needed)
            owner_id = None
            if rule_data.get('owner'):
                from backend.database.models import Owner
                owner_obj = db.query(Owner).filter(Owner.name == rule_data['owner']).first()
                if owner_obj:
                    owner_id = owner_obj.id

            # Create rule
            rule = CategorizationRule(
                name=rule_name[:100],  # Limit to 100 chars
                description=None,
                priority=int(rule_data.get('priority', 0)) if rule_data.get('priority') else 0,
                conditions=json.dumps(conditions) if conditions else "{}",
                category_tier1=rule_data.get('tier1'),
                category_tier2=rule_data.get('tier2'),
                category_tier3=rule_data.get('tier3'),
                owner_id=owner_id,
                mark_as_internal=False,  # Default to False
                is_active=True
            )

            db.add(rule)
            migrated_count += 1

            if migrated_count % 20 == 0:
                db.flush()
                logger.info(f"  Processed {migrated_count} rules...")

        db.commit()
        logger.info(f"✅ Migrated {migrated_count} rules to database")

    return migrated_count


def main():
    """Main migration script."""
    logger.info("Starting migration of Rules and Categories from Google Sheets to SQLite")

    # Load settings
    settings = load_settings()

    creds_path = settings['google_drive']['credentials_path']
    token_path = settings['google_drive']['token_path']
    spreadsheet_id = settings['google_sheets']['master_sheet_id']

    # Initialize database (create tables if they don't exist)
    logger.info("Initializing database...")
    init_db()

    # Connect to Google Sheets
    logger.info("Connecting to Google Sheets...")
    sheets = GoogleSheetsConnector(creds_path, token_path)
    if not sheets.authenticate():
        logger.error("Failed to authenticate with Google Sheets")
        return

    # Migrate categories
    categories_count = migrate_categories(sheets, spreadsheet_id)

    # Migrate rules
    rules_count = migrate_rules(sheets, spreadsheet_id)

    # Summary
    logger.info("=" * 60)
    logger.info("Migration Summary")
    logger.info("=" * 60)
    logger.info(f"Categories migrated: {categories_count}")
    logger.info(f"Rules migrated: {rules_count}")
    logger.info("=" * 60)
    logger.info("✅ Migration complete!")


if __name__ == "__main__":
    main()
