"""Setup categorization rules in Google Sheets."""

import sys
import yaml
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.connectors.google_sheets import GoogleSheetsConnector
from src.utils.logger import setup_logger

# Load settings
with open('config/settings.yaml', 'r') as f:
    settings = yaml.safe_load(f)

# Credentials paths
CREDENTIALS_PATH = settings['google_drive']['credentials_path']
TOKEN_PATH = settings['google_drive']['token_path']
SPREADSHEET_ID = settings['google_sheets']['master_sheet_id']

# Tab names
RULES_TAB = "Categorization_Rules"
OWNER_TAB = "Owner_Mapping"

logger = setup_logger(level='INFO', console=True)


def setup_categorization_rules():
    """Create and populate categorization rules sheets."""

    logger.info("Connecting to Google Sheets...")
    sheets = GoogleSheetsConnector(CREDENTIALS_PATH, TOKEN_PATH)

    # Authenticate
    if not sheets.authenticate():
        logger.error("❌ Failed to authenticate with Google Sheets")
        return False

    # ========================================
    # 1. Create Categorization_Rules tab
    # ========================================
    logger.info(f"\nCreating '{RULES_TAB}' tab...")

    # Headers
    rules_headers = [
        "Priority", "Description_Contains", "Institution_Exact",
        "Counterparty_Account_Exact", "Counterparty_Name_Contains",
        "Variable_Symbol_Exact", "Amount_CZK_Min", "Amount_CZK_Max",
        "Tier1", "Tier2", "Tier3", "Owner"
    ]

    # Basic categorization rules (~15 rules)
    rules_data = [
        # Priority, Description, Institution, CP_Account, CP_Name, VS, Min, Max, T1, T2, T3, Owner

        # Supermarkets
        [1, "Albert", "", "", "", "", "", "", "Spotreba Rodina", "Jedlo", "Supermarket", ""],
        [1, "Tesco", "", "", "", "", "", "", "Spotreba Rodina", "Jedlo", "Supermarket", ""],
        [1, "Lidl", "", "", "", "", "", "", "Spotreba Rodina", "Jedlo", "Supermarket", ""],
        [1, "Kaufland", "", "", "", "", "", "", "Spotreba Rodina", "Jedlo", "Supermarket", ""],
        [1, "Billa", "", "", "", "", "", "", "Spotreba Rodina", "Jedlo", "Supermarket", ""],

        # Fuel stations
        [1, "Shell", "", "", "", "", "", "", "Spotreba Rodina", "Doprava (Osobná)", "PHM (Osobné auto)", ""],
        [1, "OMV", "", "", "", "", "", "", "Spotreba Rodina", "Doprava (Osobná)", "PHM (Osobné auto)", ""],
        [1, "Benzina", "", "", "", "", "", "", "Spotreba Rodina", "Doprava (Osobná)", "PHM (Osobné auto)", ""],
        [1, "MOL", "", "", "", "", "", "", "Spotreba Rodina", "Doprava (Osobná)", "PHM (Osobné auto)", ""],

        # Mobile operators
        [1, "O2", "", "", "", "", "", "", "Spotreba Rodina", "Energie a Služby", "Telefón", ""],
        [1, "T-Mobile", "", "", "", "", "", "", "Spotreba Rodina", "Energie a Služby", "Telefón", ""],
        [1, "Vodafone", "", "", "", "", "", "", "Spotreba Rodina", "Energie a Služby", "Telefón", ""],

        # Transport
        [1, "Bolt", "", "", "", "", "", "", "Spotreba Rodina", "Doprava (Osobná)", "Taxi", ""],
        [1, "Uber", "", "", "", "", "", "", "Spotreba Rodina", "Doprava (Osobná)", "Taxi", ""],

        # Pharmacy
        [1, "Dr.Max", "", "", "", "", "", "", "Spotreba Rodina", "Zdravie a Starostlivosť", "Lekáreň / Vitamíny", ""],
        [1, "Benu", "", "", "", "", "", "", "Spotreba Rodina", "Zdravie a Starostlivosť", "Lekáreň / Vitamíny", ""],

        # Streaming services
        [2, "Netflix", "", "", "", "", "", "", "Spotreba Rodina", "Energie a Služby", "Subscriptions", ""],
        [2, "Spotify", "", "", "", "", "", "", "Spotreba Rodina", "Energie a Služby", "Subscriptions", ""],

        # Restaurants
        [1, "restaurant", "", "", "", "", "", "", "Spotreba Rodina", "Jedlo", "Reštaurácie", ""],
        [1, "pizza", "", "", "", "", "", "", "Spotreba Rodina", "Jedlo", "Reštaurácie", ""],
        [1, "cafe", "", "", "", "", "", "", "Spotreba Rodina", "Jedlo", "Reštaurácie", ""],
        [1, "bistro", "", "", "", "", "", "", "Spotreba Rodina", "Jedlo", "Reštaurácie", ""],
    ]

    # Combine headers and data
    rules_sheet_data = [rules_headers] + rules_data

    # Create tab and write data
    if not sheets.create_tab(SPREADSHEET_ID, RULES_TAB):
        logger.error(f"❌ Failed to create '{RULES_TAB}' tab")
        return False

    if not sheets.write_sheet(SPREADSHEET_ID, f"{RULES_TAB}!A1", rules_sheet_data):
        logger.error(f"❌ Failed to write data to '{RULES_TAB}'")
        return False

    logger.info(f"✅ Created '{RULES_TAB}' with {len(rules_data)} rules")

    # ========================================
    # 2. Create Owner_Mapping tab
    # ========================================
    logger.info(f"\nCreating '{OWNER_TAB}' tab...")

    # Headers
    owner_headers = ["Account", "Owner"]

    # Account mappings from institution configs
    owner_data = [
        # ČSOB accounts
        ["283337817/0300", "Branislav"],
        ["210621040/0300", "Branislav"],

        # Partners Bank accounts
        ["3581422554/6363", "Unknown"],
        ["1330299329/6363", "Branislav"],
        ["2106210400/6363", "Branislav"],

        # Wise (no specific account number in Wise)
        ["Wise", "Branislav"],
    ]

    # Combine headers and data
    owner_sheet_data = [owner_headers] + owner_data

    # Create tab and write data
    if not sheets.create_tab(SPREADSHEET_ID, OWNER_TAB):
        logger.error(f"❌ Failed to create '{OWNER_TAB}' tab")
        return False

    if not sheets.write_sheet(SPREADSHEET_ID, f"{OWNER_TAB}!A1", owner_sheet_data):
        logger.error(f"❌ Failed to write data to '{OWNER_TAB}'")
        return False

    logger.info(f"✅ Created '{OWNER_TAB}' with {len(owner_data)} mappings")

    # ========================================
    # Summary
    # ========================================
    logger.info("\n" + "="*70)
    logger.info("SETUP COMPLETE")
    logger.info("="*70)
    logger.info(f"✅ '{RULES_TAB}' tab created with {len(rules_data)} rules")
    logger.info(f"✅ '{OWNER_TAB}' tab created with {len(owner_data)} mappings")
    logger.info(f"\nSpreadsheet: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    logger.info("="*70)

    return True


def main():
    """Main entry point."""
    try:
        success = setup_categorization_rules()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
