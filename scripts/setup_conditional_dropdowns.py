"""Setup conditional (dependent) dropdowns for category selection in Google Sheets."""

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


def sanitize_name(name: str) -> str:
    """Sanitize name for use as named range (alphanumeric and underscore only)."""
    # Replace spaces and special characters with underscore
    sanitized = name.replace(' ', '_').replace('(', '').replace(')', '')
    sanitized = sanitized.replace('á', 'a').replace('é', 'e').replace('í', 'i')
    sanitized = sanitized.replace('ó', 'o').replace('ú', 'u').replace('ý', 'y')
    sanitized = sanitized.replace('ž', 'z').replace('š', 's').replace('č', 'c')
    sanitized = sanitized.replace('ň', 'n').replace('ť', 't').replace('ď', 'd')
    sanitized = sanitized.replace('ľ', 'l').replace('ô', 'o').replace('ä', 'a')
    sanitized = ''.join(c for c in sanitized if c.isalnum() or c == '_')
    return sanitized


def setup_conditional_dropdowns():
    """Setup conditional dropdowns using named ranges and INDIRECT."""

    logger.info("="*70)
    logger.info("SETTING UP CONDITIONAL DROPDOWNS")
    logger.info("="*70)

    # Connect to Google Sheets
    logger.info("\nConnecting to Google Sheets...")
    sheets = GoogleSheetsConnector(CREDENTIALS_PATH, TOKEN_PATH)
    if not sheets.authenticate():
        logger.error("❌ Failed to authenticate")
        return False

    # Get category tree from Sheets
    logger.info(f"\n1. Reading category tree from '{CATEGORIES_TAB}'...")
    categories_data = sheets.read_sheet(SPREADSHEET_ID, f"{CATEGORIES_TAB}!A:C")
    if not categories_data or len(categories_data) < 2:
        logger.error(f"❌ No categories found in {CATEGORIES_TAB}")
        return False

    # Parse into hierarchical structure
    category_tree = {}  # tier1 -> tier2 -> [tier3]

    for row in categories_data[1:]:  # Skip header
        if len(row) < 3:
            continue

        tier1 = row[0].strip() if row[0] else ""
        tier2 = row[1].strip() if row[1] else ""
        tier3 = row[2].strip() if row[2] else ""

        if not tier1 or not tier2 or not tier3:
            continue

        if tier1 not in category_tree:
            category_tree[tier1] = {}

        if tier2 not in category_tree[tier1]:
            category_tree[tier1][tier2] = []

        if tier3 not in category_tree[tier1][tier2]:
            category_tree[tier1][tier2].append(tier3)

    logger.info(f"✅ Loaded {len(category_tree)} tier1 categories")

    # ========================================
    # 2. Create helper columns with tier2/tier3 options
    # ========================================
    logger.info(f"\n2. Creating helper columns for conditional dropdowns...")

    # We'll write tier2 and tier3 options in separate columns, starting from column I onwards
    # Each tier1 gets a column for its tier2 options
    # Each tier2 gets a column for its tier3 options

    helper_data = []
    column_index = 8  # Start at column I (0-indexed: A=0, I=8)

    tier1_to_col = {}  # Maps tier1 name to column letter
    tier2_to_col = {}  # Maps tier2 name to column letter

    # Build header row and data
    max_rows = 0

    # First, tier2 options for each tier1
    tier2_columns = []
    for tier1 in sorted(category_tree.keys()):
        tier2_list = sorted(category_tree[tier1].keys())
        tier2_columns.append({
            'name': tier1,
            'values': tier2_list,
            'col_letter': chr(65 + column_index)  # Convert to letter
        })
        tier1_to_col[tier1] = chr(65 + column_index)
        column_index += 1
        max_rows = max(max_rows, len(tier2_list) + 1)

    # Then, tier3 options for each tier2
    tier3_columns = []
    for tier1 in sorted(category_tree.keys()):
        for tier2 in sorted(category_tree[tier1].keys()):
            tier3_list = category_tree[tier1][tier2]
            tier3_columns.append({
                'name': tier2,
                'values': tier3_list,
                'col_letter': chr(65 + column_index)
            })
            tier2_to_col[tier2] = chr(65 + column_index)
            column_index += 1
            max_rows = max(max_rows, len(tier3_list) + 1)

    # Build the helper data grid
    for row_idx in range(max_rows):
        row = []

        # Tier2 columns
        for col_info in tier2_columns:
            if row_idx == 0:
                row.append(f"{col_info['name']}_Tier2")
            elif row_idx - 1 < len(col_info['values']):
                row.append(col_info['values'][row_idx - 1])
            else:
                row.append("")

        # Tier3 columns
        for col_info in tier3_columns:
            if row_idx == 0:
                row.append(f"{col_info['name']}_Tier3")
            elif row_idx - 1 < len(col_info['values']):
                row.append(col_info['values'][row_idx - 1])
            else:
                row.append("")

        helper_data.append(row)

    # Write helper data starting at column I
    start_col = chr(65 + 8)  # Column I
    if not sheets.write_sheet(SPREADSHEET_ID, f"{CATEGORIES_TAB}!{start_col}1", helper_data):
        logger.error(f"❌ Failed to write helper columns")
        return False

    logger.info(f"✅ Created {len(tier2_columns)} tier2 helper columns")
    logger.info(f"✅ Created {len(tier3_columns)} tier3 helper columns")

    # ========================================
    # 3. Create named ranges
    # ========================================
    logger.info(f"\n3. Creating named ranges...")

    named_ranges = []

    # Named range for tier1 (all tier1 values)
    tier1_list = sorted(category_tree.keys())
    tier1_range = f"{CATEGORIES_TAB}!E2:E{len(tier1_list)+1}"

    # Named ranges for tier2 options (one per tier1)
    for col_info in tier2_columns:
        range_name = f"Tier2_{sanitize_name(col_info['name'])}"
        col_letter = col_info['col_letter']
        num_values = len(col_info['values'])
        range_ref = f"{CATEGORIES_TAB}!{col_letter}2:{col_letter}{num_values+1}"

        named_ranges.append({
            'name': range_name,
            'range': range_ref
        })

    # Named ranges for tier3 options (one per tier2)
    for col_info in tier3_columns:
        range_name = f"Tier3_{sanitize_name(col_info['name'])}"
        col_letter = col_info['col_letter']
        num_values = len(col_info['values'])
        range_ref = f"{CATEGORIES_TAB}!{col_letter}2:{col_letter}{num_values+1}"

        named_ranges.append({
            'name': range_name,
            'range': range_ref
        })

    # Create named ranges via API
    requests = []
    for nr in named_ranges:
        # Parse range (e.g., "Categories!I2:I5")
        parts = nr['range'].split('!')
        sheet_name = parts[0]
        range_str = parts[1]

        requests.append({
            'addNamedRange': {
                'namedRange': {
                    'name': nr['name'],
                    'range': {
                        'sheetId': get_sheet_id(sheets.service, SPREADSHEET_ID, sheet_name),
                        'startRowIndex': 1,  # Row 2 (0-indexed)
                        'endRowIndex': int(range_str.split(':')[1][1:]),  # End row
                        'startColumnIndex': ord(range_str[0]) - 65,  # Column letter to index
                        'endColumnIndex': ord(range_str.split(':')[1][0]) - 65 + 1
                    }
                }
            }
        })

    try:
        # Delete existing named ranges first (to avoid conflicts)
        logger.info(f"   Deleting old named ranges...")
        spreadsheet = sheets.service.spreadsheets().get(
            spreadsheetId=SPREADSHEET_ID
        ).execute()

        delete_requests = []
        for named_range in spreadsheet.get('namedRanges', []):
            if named_range['name'].startswith('Tier2_') or named_range['name'].startswith('Tier3_'):
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

        # Create new named ranges
        body = {'requests': requests}
        sheets.service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=body
        ).execute()

        logger.info(f"✅ Created {len(named_ranges)} named ranges")
    except Exception as e:
        logger.error(f"❌ Failed to create named ranges: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

    # ========================================
    # 4. Set up conditional data validation
    # ========================================
    logger.info(f"\n4. Setting up conditional validation on '{RULES_TAB}'...")

    rules_sheet_id = get_sheet_id(sheets.service, SPREADSHEET_ID, RULES_TAB)
    if rules_sheet_id is None:
        logger.error(f"❌ Could not find sheet ID for '{RULES_TAB}'")
        return False

    validation_requests = []

    # Tier1 validation (column I) - static list
    categories_sheet_id = get_sheet_id(sheets.service, SPREADSHEET_ID, CATEGORIES_TAB)

    validation_requests.append({
        'setDataValidation': {
            'range': {
                'sheetId': rules_sheet_id,
                'startRowIndex': 1,
                'endRowIndex': 1000,
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

    # Tier2 validation (column J) - conditional on Tier1 (column I)
    # Use INDIRECT formula: =INDIRECT("Tier2_"&SUBSTITUTE(I2," ","_"))
    validation_requests.append({
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
                    'type': 'CUSTOM_FORMULA',
                    'values': [{'userEnteredValue': '=COUNTIF(INDIRECT("Tier2_"&SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(I2," ","_"),"(",""),")","")),$J2)>0'}]
                },
                'showCustomUi': True,
                'strict': False,
                'inputMessage': 'Select Tier1 first, then choose from matching Tier2 options'
            }
        }
    })

    # Tier3 validation (column K) - conditional on Tier2 (column J)
    validation_requests.append({
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
                    'type': 'CUSTOM_FORMULA',
                    'values': [{'userEnteredValue': '=COUNTIF(INDIRECT("Tier3_"&SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(J2," ","_"),"(",""),")","")),$K2)>0'}]
                },
                'showCustomUi': True,
                'strict': False,
                'inputMessage': 'Select Tier2 first, then choose from matching Tier3 options'
            }
        }
    })

    try:
        body = {'requests': validation_requests}
        sheets.service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=body
        ).execute()
        logger.info(f"✅ Added conditional validation (Tier2 depends on Tier1, Tier3 on Tier2)")
    except Exception as e:
        logger.error(f"❌ Failed to add validation: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

    # ========================================
    # Summary
    # ========================================
    logger.info("\n" + "="*70)
    logger.info("SETUP COMPLETE")
    logger.info("="*70)
    logger.info(f"✅ Helper columns created in '{CATEGORIES_TAB}' (columns I+)")
    logger.info(f"✅ {len(named_ranges)} named ranges created")
    logger.info(f"✅ Conditional dropdowns configured:")
    logger.info(f"   - Tier1: Static list (7 options)")
    logger.info(f"   - Tier2: Depends on Tier1 selection")
    logger.info(f"   - Tier3: Depends on Tier2 selection")
    logger.info(f"\n📝 How to use:")
    logger.info(f"   1. In {RULES_TAB}, select Tier1 from dropdown")
    logger.info(f"   2. Tier2 dropdown will show only valid options for that Tier1")
    logger.info(f"   3. Tier3 dropdown will show only valid options for that Tier2")
    logger.info(f"\nSpreadsheet: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    logger.info("="*70)

    return True


def main():
    """Main entry point."""
    try:
        success = setup_conditional_dropdowns()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
