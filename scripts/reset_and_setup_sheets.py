"""Complete reset and setup of categorization sheets from scratch."""

import sys
import yaml
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.connectors.google_sheets import GoogleSheetsConnector
from src.utils.logger import setup_logger

logger = setup_logger(level='INFO', console=True)

# Load settings
with open('config/settings.yaml', 'r') as f:
    settings = yaml.safe_load(f)

CREDENTIALS_PATH = settings['google_drive']['credentials_path']
TOKEN_PATH = settings['google_drive']['token_path']
SPREADSHEET_ID = settings['google_sheets']['master_sheet_id']

# Tabs to delete and recreate
TABS_TO_RESET = ["Lists", "Categories", "Categorization_Rules", "Owner_Mapping"]


def sanitize_name(name: str) -> str:
    """Sanitize name for use as named range."""
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ý': 'y',
        'ž': 'z', 'š': 's', 'č': 'c', 'ň': 'n', 'ť': 't', 'ď': 'd',
        'ľ': 'l', 'ô': 'o', 'ä': 'a', 'ŕ': 'r',
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U', 'Ý': 'Y',
        'Ž': 'Z', 'Š': 'S', 'Č': 'C', 'Ň': 'N', 'Ť': 'T', 'Ď': 'D',
        'Ľ': 'L', 'Ô': 'O', 'Ä': 'A', 'Ŕ': 'R'
    }

    sanitized = name
    for old, new in replacements.items():
        sanitized = sanitized.replace(old, new)

    sanitized = sanitized.replace(' ', '_')
    sanitized = sanitized.replace('(', '').replace(')', '')
    sanitized = sanitized.replace('/', '_')
    sanitized = sanitized.replace('&', 'a')
    sanitized = ''.join(c for c in sanitized if c.isalnum() or c == '_')

    return sanitized


def get_sheet_id(sheets_service, spreadsheet_id: str, tab_name: str) -> int:
    """Get the sheet ID for a given tab name."""
    try:
        spreadsheet = sheets_service.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        ).execute()

        for sheet in spreadsheet.get('sheets', []):
            if sheet['properties']['title'] == tab_name:
                return sheet['properties']['sheetId']

        return None
    except Exception as e:
        logger.error(f"Error getting sheet ID: {e}")
        return None


def delete_tab(sheets_service, spreadsheet_id: str, tab_name: str) -> bool:
    """Delete a tab if it exists."""
    try:
        sheet_id = get_sheet_id(sheets_service, spreadsheet_id, tab_name)
        if sheet_id is None:
            logger.info(f"   Tab '{tab_name}' doesn't exist, skipping")
            return True

        body = {
            'requests': [{
                'deleteSheet': {
                    'sheetId': sheet_id
                }
            }]
        }

        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()

        logger.info(f"   ✅ Deleted '{tab_name}'")
        return True

    except Exception as e:
        logger.error(f"   ❌ Failed to delete '{tab_name}': {e}")
        return False


def reset_and_setup():
    """Complete reset and setup."""

    logger.info("="*70)
    logger.info("COMPLETE RESET AND SETUP FROM SCRATCH")
    logger.info("="*70)

    # Connect
    logger.info("\n1. Connecting to Google Sheets...")
    sheets = GoogleSheetsConnector(CREDENTIALS_PATH, TOKEN_PATH)
    if not sheets.authenticate():
        logger.error("❌ Failed to authenticate")
        return False

    # Delete all named ranges first
    logger.info("\n2. Deleting all named ranges...")
    try:
        spreadsheet = sheets.service.spreadsheets().get(
            spreadsheetId=SPREADSHEET_ID
        ).execute()

        delete_requests = []
        for named_range in spreadsheet.get('namedRanges', []):
            delete_requests.append({
                'deleteNamedRange': {
                    'namedRangeId': named_range['namedRangeId']
                }
            })

        if delete_requests:
            body = {'requests': delete_requests}
            sheets.service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=body
            ).execute()
            logger.info(f"   ✅ Deleted {len(delete_requests)} named ranges")
        else:
            logger.info("   No named ranges to delete")

    except Exception as e:
        logger.warning(f"   Could not delete named ranges: {e}")

    # Delete tabs
    logger.info("\n3. Deleting existing tabs...")
    for tab in TABS_TO_RESET:
        delete_tab(sheets.service, SPREADSHEET_ID, tab)

    # Get category tree from config
    logger.info("\n4. Loading category tree from config...")
    with open('config/categorization.yaml', 'r', encoding='utf-8') as f:
        cat_config = yaml.safe_load(f)

    # Build category tree structure
    category_tree = {}
    tier1_display = {}
    tier2_display = {}

    # Since we removed category_tree from YAML, we'll create a basic structure
    # You can edit this manually in the Lists sheet after
    logger.info("   Creating basic category structure...")

    basic_categories = {
        'Prijmy': {
            'Zamestnanie': ['Mzda', 'Bonusy'],
            'Podnikanie': ['Fakturacia_Prijem'],
        },
        'Spotreba_Rodina': {
            'Byvanie': ['Hypoteka_Najom', 'Energie'],
            'Jedlo': ['Supermarket', 'Restauracie'],
        },
        'Nezaradene': {
            'Needs_Review': ['Unknown_Transaction'],
        }
    }

    category_tree = basic_categories

    # Create Categories tab
    logger.info("\n5. Creating 'Categories' tab...")
    if not sheets.create_tab(SPREADSHEET_ID, "Categories"):
        logger.error("❌ Failed to create Categories tab")
        return False

    categories_data = [["Tier1", "Tier2", "Tier3"]]
    for t1_safe, t2_dict in category_tree.items():
        for t2_safe, t3_list in t2_dict.items():
            for t3_safe in t3_list:
                categories_data.append([t1_safe, t2_safe, t3_safe])

    if not sheets.write_sheet(SPREADSHEET_ID, "Categories!A1", categories_data):
        logger.error("❌ Failed to write Categories")
        return False

    logger.info(f"   ✅ Created with {len(categories_data)-1} rows")

    # Create Lists tab
    logger.info("\n6. Creating 'Lists' tab...")
    if not sheets.create_tab(SPREADSHEET_ID, "Lists"):
        logger.error("❌ Failed to create Lists tab")
        return False

    tier1_sorted = sorted(category_tree.keys())

    # Build Lists structure
    grid = []
    max_rows = 10

    for row_idx in range(max_rows):
        row = []

        # Column A: Tier1
        if row_idx == 0:
            row.append("Tier1")
        elif row_idx - 1 < len(tier1_sorted):
            row.append(tier1_sorted[row_idx - 1])
        else:
            row.append("")

        # Columns B+: Tier2 lists
        for t1_safe in tier1_sorted:
            tier2_list = sorted(category_tree[t1_safe].keys())
            if row_idx == 0:
                row.append(t1_safe)
            elif row_idx - 1 < len(tier2_list):
                row.append(tier2_list[row_idx - 1])
            else:
                row.append("")

        # Tier3 lists
        for t1_safe in tier1_sorted:
            for t2_safe in sorted(category_tree[t1_safe].keys()):
                tier3_list = category_tree[t1_safe][t2_safe]
                if row_idx == 0:
                    row.append(t2_safe)
                elif row_idx - 1 < len(tier3_list):
                    row.append(tier3_list[row_idx - 1])
                else:
                    row.append("")

        grid.append(row)

    if not sheets.write_sheet(SPREADSHEET_ID, "Lists!A1", grid):
        logger.error("❌ Failed to write Lists")
        return False

    logger.info(f"   ✅ Created with {len(grid)} rows, {len(grid[0])} columns")

    # Create named ranges
    logger.info("\n7. Creating named ranges...")
    lists_sheet_id = get_sheet_id(sheets.service, SPREADSHEET_ID, "Lists")

    named_range_requests = []
    created_ranges = set()

    # Tier1 range
    named_range_requests.append({
        'addNamedRange': {
            'namedRange': {
                'name': 'Tier1',
                'range': {
                    'sheetId': lists_sheet_id,
                    'startRowIndex': 1,
                    'endRowIndex': len(tier1_sorted) + 1,
                    'startColumnIndex': 0,
                    'endColumnIndex': 1
                }
            }
        }
    })
    created_ranges.add('Tier1')

    # Tier2 ranges
    col_idx = 1
    for t1_safe in tier1_sorted:
        tier2_list = sorted(category_tree[t1_safe].keys())
        if t1_safe not in created_ranges:
            named_range_requests.append({
                'addNamedRange': {
                    'namedRange': {
                        'name': t1_safe,
                        'range': {
                            'sheetId': lists_sheet_id,
                            'startRowIndex': 1,
                            'endRowIndex': len(tier2_list) + 1,
                            'startColumnIndex': col_idx,
                            'endColumnIndex': col_idx + 1
                        }
                    }
                }
            })
            created_ranges.add(t1_safe)
        col_idx += 1

    # Tier3 ranges
    for t1_safe in tier1_sorted:
        for t2_safe in sorted(category_tree[t1_safe].keys()):
            tier3_list = category_tree[t1_safe][t2_safe]
            if t2_safe not in created_ranges:
                named_range_requests.append({
                    'addNamedRange': {
                        'namedRange': {
                            'name': t2_safe,
                            'range': {
                                'sheetId': lists_sheet_id,
                                'startRowIndex': 1,
                                'endRowIndex': len(tier3_list) + 1,
                                'startColumnIndex': col_idx,
                                'endColumnIndex': col_idx + 1
                            }
                        }
                    }
                })
                created_ranges.add(t2_safe)
            col_idx += 1

    body = {'requests': named_range_requests}
    sheets.service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body=body
    ).execute()

    logger.info(f"   ✅ Created {len(named_range_requests)} named ranges")

    # Create Categorization_Rules tab
    logger.info("\n8. Creating 'Categorization_Rules' tab...")
    if not sheets.create_tab(SPREADSHEET_ID, "Categorization_Rules"):
        logger.error("❌ Failed to create Categorization_Rules")
        return False

    rules_headers = [
        "Priority", "Description_Contains", "Institution_Exact",
        "Counterparty_Account_Exact", "Counterparty_Name_Contains",
        "Variable_Symbol_Exact", "Amount_CZK_Min", "Amount_CZK_Max",
        "Tier1", "Tier2", "Tier3", "Owner"
    ]

    rules_data = [rules_headers]  # Empty, ready for user to add rules

    if not sheets.write_sheet(SPREADSHEET_ID, "Categorization_Rules!A1", rules_data):
        logger.error("❌ Failed to write Categorization_Rules")
        return False

    logger.info("   ✅ Created (empty, ready for rules)")

    # Create Owner_Mapping tab
    logger.info("\n9. Creating 'Owner_Mapping' tab...")
    if not sheets.create_tab(SPREADSHEET_ID, "Owner_Mapping"):
        logger.error("❌ Failed to create Owner_Mapping")
        return False

    owner_headers = ["Account", "Owner"]
    owner_data = [owner_headers]  # Empty, ready for user to add mappings

    if not sheets.write_sheet(SPREADSHEET_ID, "Owner_Mapping!A1", owner_data):
        logger.error("❌ Failed to write Owner_Mapping")
        return False

    logger.info("   ✅ Created (empty, ready for mappings)")

    # Summary
    logger.info("\n" + "="*70)
    logger.info("RESET COMPLETE - FRESH START")
    logger.info("="*70)
    logger.info("✅ All categorization tabs deleted and recreated")
    logger.info("✅ All named ranges reset")
    logger.info("✅ Basic structure in place")
    logger.info(f"\n📝 NEXT STEPS:")
    logger.info(f"\n1. Edit 'Lists' sheet to add your categories")
    logger.info(f"2. Edit 'Categories' tab to match")
    logger.info(f"3. Set up dropdowns in 'Categorization_Rules':")
    logger.info(f"   - Column I (Tier1): =Tier1")
    logger.info(f"   - Column J (Tier2): =INDIRECT(I2)")
    logger.info(f"   - Column K (Tier3): =INDIRECT(J2)")
    logger.info(f"4. Add your rules to 'Categorization_Rules'")
    logger.info(f"5. Add account mappings to 'Owner_Mapping'")
    logger.info(f"\nSpreadsheet: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    logger.info("="*70)

    return True


def main():
    """Main entry point."""
    try:
        success = reset_and_setup()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
