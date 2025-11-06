"""Setup category structure and dropdowns in Google Sheets."""

import sys
import yaml
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.connectors.google_sheets import GoogleSheetsConnector
from src.utils.logger import setup_logger

logger = setup_logger(level='INFO', console=True)

# Load settings
with open('config/settings.yaml', 'r') as f:
    settings = yaml.safe_load(f)

# Load categorization config to get category_tree
with open('config/categorization.yaml', 'r', encoding='utf-8') as f:
    cat_config = yaml.safe_load(f)

CREDENTIALS_PATH = settings['google_drive']['credentials_path']
TOKEN_PATH = settings['google_drive']['token_path']
SPREADSHEET_ID = settings['google_sheets']['master_sheet_id']

CATEGORIES_TAB = "Categories"
RULES_TAB = "Categorization_Rules"


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


def setup_categories_and_dropdowns():
    """Create Categories tab and setup dropdowns."""

    logger.info("="*70)
    logger.info("SETTING UP CATEGORY DROPDOWNS")
    logger.info("="*70)

    # Connect to Google Sheets
    logger.info("\nConnecting to Google Sheets...")
    sheets = GoogleSheetsConnector(CREDENTIALS_PATH, TOKEN_PATH)
    if not sheets.authenticate():
        logger.error("❌ Failed to authenticate")
        return False

    category_tree = cat_config.get('category_tree', [])

    # ========================================
    # 1. Create Categories tab with full tree
    # ========================================
    logger.info(f"\n1. Creating '{CATEGORIES_TAB}' tab with category tree...")

    # Build category data: one row per complete path (tier1 > tier2 > tier3)
    categories_data = [["Tier1", "Tier2", "Tier3"]]  # Header

    # Collect all unique values for dropdowns
    all_tier1 = set()
    all_tier2 = set()
    all_tier3 = set()

    for tier1_item in category_tree:
        tier1 = tier1_item['tier1']
        all_tier1.add(tier1)

        tier2_categories = tier1_item.get('tier2_categories', [])
        for tier2_item in tier2_categories:
            tier2 = tier2_item['tier2']
            all_tier2.add(tier2)

            tier3_list = tier2_item.get('tier3', [])
            for tier3 in tier3_list:
                all_tier3.add(tier3)
                categories_data.append([tier1, tier2, tier3])

    # Sort for consistency
    tier1_list = sorted(list(all_tier1))
    tier2_list = sorted(list(all_tier2))
    tier3_list = sorted(list(all_tier3))

    # Create tab
    if not sheets.create_tab(SPREADSHEET_ID, CATEGORIES_TAB):
        logger.error(f"❌ Failed to create '{CATEGORIES_TAB}' tab")
        return False

    # Write category tree
    if not sheets.write_sheet(SPREADSHEET_ID, f"{CATEGORIES_TAB}!A1", categories_data):
        logger.error(f"❌ Failed to write category data")
        return False

    logger.info(f"✅ Created '{CATEGORIES_TAB}' with {len(categories_data)-1} category paths")

    # ========================================
    # 2. Add dropdown lists in separate columns
    # ========================================
    logger.info(f"\n2. Adding dropdown option lists...")

    # Column E: All Tier1 options
    # Column F: All Tier2 options
    # Column G: All Tier3 options
    dropdown_lists = [
        ["All Tier1 Options"] + tier1_list,
        ["All Tier2 Options"] + tier2_list,
        ["All Tier3 Options"] + tier3_list
    ]

    # Pad to same length
    max_len = max(len(lst) for lst in dropdown_lists)
    for lst in dropdown_lists:
        while len(lst) < max_len:
            lst.append("")

    # Transpose for writing
    transposed = [[dropdown_lists[j][i] if i < len(dropdown_lists[j]) else ""
                   for j in range(len(dropdown_lists))]
                  for i in range(max_len)]

    if not sheets.write_sheet(SPREADSHEET_ID, f"{CATEGORIES_TAB}!E1", transposed):
        logger.error(f"❌ Failed to write dropdown lists")
        return False

    logger.info(f"✅ Added dropdown lists:")
    logger.info(f"   - {len(tier1_list)} Tier1 options")
    logger.info(f"   - {len(tier2_list)} Tier2 options")
    logger.info(f"   - {len(tier3_list)} Tier3 options")

    # ========================================
    # 3. Set up data validation on Categorization_Rules
    # ========================================
    logger.info(f"\n3. Setting up dropdown validation on '{RULES_TAB}'...")

    # Get sheet IDs
    rules_sheet_id = get_sheet_id(sheets.service, SPREADSHEET_ID, RULES_TAB)
    if rules_sheet_id is None:
        logger.error(f"❌ Could not find sheet ID for '{RULES_TAB}'")
        return False

    # Define validation rules
    # Tier1 is column I (index 8), Tier2 is column J (9), Tier3 is column K (10)
    requests = []

    # Tier1 validation (column I, rows 2+)
    requests.append({
        'setDataValidation': {
            'range': {
                'sheetId': rules_sheet_id,
                'startRowIndex': 1,  # Row 2 (0-indexed)
                'endRowIndex': 1000,  # Apply to 1000 rows
                'startColumnIndex': 8,  # Column I
                'endColumnIndex': 9
            },
            'rule': {
                'condition': {
                    'type': 'ONE_OF_RANGE',
                    'values': [{
                        'userEnteredValue': f'={CATEGORIES_TAB}!$E$2:$E${len(tier1_list)+1}'
                    }]
                },
                'showCustomUi': True,
                'strict': False
            }
        }
    })

    # Tier2 validation (column J, rows 2+) - all tier2 options
    requests.append({
        'setDataValidation': {
            'range': {
                'sheetId': rules_sheet_id,
                'startRowIndex': 1,
                'endRowIndex': 1000,
                'startColumnIndex': 9,  # Column J
                'endColumnIndex': 10
            },
            'rule': {
                'condition': {
                    'type': 'ONE_OF_RANGE',
                    'values': [{
                        'userEnteredValue': f'={CATEGORIES_TAB}!$F$2:$F${len(tier2_list)+1}'
                    }]
                },
                'showCustomUi': True,
                'strict': False
            }
        }
    })

    # Tier3 validation (column K, rows 2+) - all tier3 options
    requests.append({
        'setDataValidation': {
            'range': {
                'sheetId': rules_sheet_id,
                'startRowIndex': 1,
                'endRowIndex': 1000,
                'startColumnIndex': 10,  # Column K
                'endColumnIndex': 11
            },
            'rule': {
                'condition': {
                    'type': 'ONE_OF_RANGE',
                    'values': [{
                        'userEnteredValue': f'={CATEGORIES_TAB}!$G$2:$G${len(tier3_list)+1}'
                    }]
                },
                'showCustomUi': True,
                'strict': False
            }
        }
    })

    # Execute batch update
    try:
        body = {'requests': requests}
        sheets.service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=body
        ).execute()
        logger.info(f"✅ Added dropdown validation to Tier1, Tier2, Tier3 columns")
    except Exception as e:
        logger.error(f"❌ Failed to add validation: {e}")
        return False

    # ========================================
    # Summary
    # ========================================
    logger.info("\n" + "="*70)
    logger.info("SETUP COMPLETE")
    logger.info("="*70)
    logger.info(f"✅ '{CATEGORIES_TAB}' tab created with {len(categories_data)-1} category paths")
    logger.info(f"✅ Dropdown lists created in columns E-G")
    logger.info(f"✅ Data validation added to '{RULES_TAB}' (Tier1/2/3 columns)")
    logger.info(f"\n📝 Note: Dropdowns show ALL options (not conditional)")
    logger.info(f"   You can reference '{CATEGORIES_TAB}' tab to see valid combinations")
    logger.info(f"\nSpreadsheet: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    logger.info("="*70)

    return True


def main():
    """Main entry point."""
    try:
        success = setup_categories_and_dropdowns()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
