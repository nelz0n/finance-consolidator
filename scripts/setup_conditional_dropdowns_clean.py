"""Setup conditional dropdowns using Lists sheet and named ranges with INDIRECT."""

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

LISTS_TAB = "Lists"
CATEGORIES_TAB = "Categories"
RULES_TAB = "Categorization_Rules"


def sanitize_name(name: str) -> str:
    """
    Sanitize name for use as named range.
    Replace spaces and special characters with underscore.
    Remove Slovak diacritics.
    """
    # Replace diacritics
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

    # Replace spaces and special characters
    sanitized = sanitized.replace(' ', '_')
    sanitized = sanitized.replace('(', '').replace(')', '')
    sanitized = sanitized.replace('/', '_')
    sanitized = sanitized.replace('&', 'a')

    # Keep only alphanumeric and underscore
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


def setup_conditional_dropdowns():
    """Setup conditional dropdowns using Lists sheet and INDIRECT."""

    logger.info("="*70)
    logger.info("SETTING UP CONDITIONAL DROPDOWNS (CLEAN APPROACH)")
    logger.info("="*70)

    # Connect to Google Sheets
    logger.info("\nConnecting to Google Sheets...")
    sheets = GoogleSheetsConnector(CREDENTIALS_PATH, TOKEN_PATH)
    if not sheets.authenticate():
        logger.error("❌ Failed to authenticate")
        return False

    # ========================================
    # 1. Read category tree from Categories tab
    # ========================================
    logger.info(f"\n1. Reading category tree from '{CATEGORIES_TAB}'...")
    categories_data = sheets.read_sheet(SPREADSHEET_ID, f"{CATEGORIES_TAB}!A:C")
    if not categories_data or len(categories_data) < 2:
        logger.error(f"❌ No categories found in {CATEGORIES_TAB}")
        return False

    # Parse into hierarchical structure
    category_tree = {}  # tier1 -> tier2 -> [tier3]
    tier1_display = {}  # safe_name -> display_name
    tier2_display = {}  # safe_name -> display_name

    for row in categories_data[1:]:  # Skip header
        if len(row) < 3:
            continue

        tier1 = row[0].strip() if row[0] else ""
        tier2 = row[1].strip() if row[1] else ""
        tier3 = row[2].strip() if row[2] else ""

        if not tier1 or not tier2 or not tier3:
            continue

        tier1_safe = sanitize_name(tier1)
        tier2_safe = sanitize_name(tier2)
        tier3_safe = sanitize_name(tier3)

        tier1_display[tier1_safe] = tier1
        tier2_display[tier2_safe] = tier2

        if tier1_safe not in category_tree:
            category_tree[tier1_safe] = {}

        if tier2_safe not in category_tree[tier1_safe]:
            category_tree[tier1_safe][tier2_safe] = []

        if tier3_safe not in category_tree[tier1_safe][tier2_safe]:
            category_tree[tier1_safe][tier2_safe].append(tier3_safe)

    logger.info(f"✅ Parsed {len(category_tree)} tier1 categories")

    # ========================================
    # 2. Create Lists sheet with proper structure
    # ========================================
    logger.info(f"\n2. Creating '{LISTS_TAB}' sheet...")

    # Create Lists tab
    if not sheets.create_tab(SPREADSHEET_ID, LISTS_TAB):
        logger.error(f"❌ Failed to create '{LISTS_TAB}' tab")
        return False

    # Build Lists sheet structure
    # Column A: Tier1 list
    # Columns B, C, D...: Tier2 lists (header = tier1 safe name)
    # Columns M+: Tier3 lists (header = tier2 safe name)

    tier1_sorted = sorted(category_tree.keys())
    max_tier2_count = max(len(category_tree[t1]) for t1 in tier1_sorted)

    # Count total tier3 columns needed
    total_tier3_cols = sum(len(category_tree[t1]) for t1 in tier1_sorted)

    # Calculate max rows needed
    max_rows = 1  # Header
    max_rows = max(max_rows, len(tier1_sorted) + 1)

    for t1 in tier1_sorted:
        for t2 in category_tree[t1].keys():
            max_rows = max(max_rows, len(category_tree[t1][t2]) + 1)

    # Build the grid
    grid = []

    # Build rows
    for row_idx in range(max_rows):
        row = []

        # Column A: Tier1 list
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
                row.append(t1_safe)  # Header = tier1 safe name
            elif row_idx - 1 < len(tier2_list):
                row.append(tier2_list[row_idx - 1])
            else:
                row.append("")

        # Columns M+: Tier3 lists
        for t1_safe in tier1_sorted:
            for t2_safe in sorted(category_tree[t1_safe].keys()):
                tier3_list = category_tree[t1_safe][t2_safe]
                if row_idx == 0:
                    row.append(t2_safe)  # Header = tier2 safe name
                elif row_idx - 1 < len(tier3_list):
                    row.append(tier3_list[row_idx - 1])
                else:
                    row.append("")

        grid.append(row)

    # Write to Lists sheet
    if not sheets.write_sheet(SPREADSHEET_ID, f"{LISTS_TAB}!A1", grid):
        logger.error(f"❌ Failed to write Lists sheet")
        return False

    logger.info(f"✅ Created Lists sheet with {len(grid)} rows, {len(grid[0])} columns")
    logger.info(f"   - Column A: Tier1 list ({len(tier1_sorted)} items)")
    logger.info(f"   - Columns B-{chr(65 + len(tier1_sorted))}: Tier2 lists ({len(tier1_sorted)} lists)")
    logger.info(f"   - Columns {chr(65 + len(tier1_sorted) + 1)}+: Tier3 lists ({total_tier3_cols} lists)")

    # ========================================
    # 3. Create named ranges
    # ========================================
    logger.info(f"\n3. Creating named ranges...")

    lists_sheet_id = get_sheet_id(sheets.service, SPREADSHEET_ID, LISTS_TAB)
    if lists_sheet_id is None:
        logger.error(f"❌ Could not find sheet ID for '{LISTS_TAB}'")
        return False

    # Delete ALL existing named ranges (to avoid conflicts)
    try:
        spreadsheet = sheets.service.spreadsheets().get(
            spreadsheetId=SPREADSHEET_ID
        ).execute()

        delete_requests = []
        for named_range in spreadsheet.get('namedRanges', []):
            # Delete all ranges (we'll recreate the ones we need)
            delete_requests.append({
                'deleteNamedRange': {
                    'namedRangeId': named_range['namedRangeId']
                }
            })

        if delete_requests:
            logger.info(f"   Deleting {len(delete_requests)} existing named ranges...")
            body = {'requests': delete_requests}
            sheets.service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=body
            ).execute()
    except Exception as e:
        logger.warning(f"Could not delete old ranges: {e}")

    # Create new named ranges
    named_range_requests = []
    created_ranges = set()  # Track created range names to avoid duplicates

    # Tier1 range (Column A)
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

    # Tier2 ranges (one per tier1)
    col_idx = 1
    for t1_safe in tier1_sorted:
        tier2_list = sorted(category_tree[t1_safe].keys())

        # Skip if already created
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

    # Tier3 ranges (one per tier2)
    for t1_safe in tier1_sorted:
        for t2_safe in sorted(category_tree[t1_safe].keys()):
            tier3_list = category_tree[t1_safe][t2_safe]

            # Skip if already created
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

    # Execute batch update
    try:
        body = {'requests': named_range_requests}
        sheets.service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=body
        ).execute()
        logger.info(f"✅ Created {len(named_range_requests)} named ranges")
    except Exception as e:
        logger.error(f"❌ Failed to create named ranges: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

    # ========================================
    # Summary & Instructions
    # ========================================
    logger.info("\n" + "="*70)
    logger.info("SETUP COMPLETE - INFRASTRUCTURE READY")
    logger.info("="*70)
    logger.info(f"✅ '{LISTS_TAB}' sheet created with category structure")
    logger.info(f"✅ {len(named_range_requests)} named ranges created")
    logger.info(f"\n📝 NEXT STEPS (Manual - 2 minutes):")
    logger.info(f"\n1. Go to '{RULES_TAB}' tab")
    logger.info(f"\n2. Select column I (Tier1), click Data > Data validation")
    logger.info(f"   - Criteria: Dropdown (from a range)")
    logger.info(f"   - Range: =Tier1")
    logger.info(f"\n3. Select column J (Tier2), click Data > Data validation")
    logger.info(f"   - Criteria: Dropdown (from a range)")
    logger.info(f"   - Range: =INDIRECT(I2)")
    logger.info(f"\n4. Select column K (Tier3), click Data > Data validation")
    logger.info(f"   - Criteria: Dropdown (from a range)")
    logger.info(f"   - Range: =INDIRECT(J2)")
    logger.info(f"\n💡 How it works:")
    logger.info(f"   - Select Tier1 → Tier2 dropdown shows only valid options")
    logger.info(f"   - Select Tier2 → Tier3 dropdown shows only valid options")
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
