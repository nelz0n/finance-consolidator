"""Interactive wizard to add a new institution configuration."""

import sys
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import setup_logger

logger = setup_logger(level='INFO', console=True)


def get_input(prompt: str, default: Optional[str] = None, required: bool = True) -> str:
    """Get user input with optional default value."""
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "

    while True:
        value = input(full_prompt).strip()

        if not value and default:
            return default

        if not value and required:
            print("  This field is required. Please enter a value.")
            continue

        return value


def get_yes_no(prompt: str, default: bool = False) -> bool:
    """Get yes/no input from user."""
    default_str = "Y/n" if default else "y/N"
    while True:
        response = input(f"{prompt} [{default_str}]: ").strip().lower()

        if not response:
            return default

        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("  Please enter 'y' or 'n'")


def get_choice(prompt: str, choices: List[str], default: Optional[str] = None) -> str:
    """Get choice from list of options."""
    print(f"\n{prompt}")
    for i, choice in enumerate(choices, 1):
        marker = " (default)" if choice == default else ""
        print(f"  {i}. {choice}{marker}")

    while True:
        response = input(f"\nEnter choice [1-{len(choices)}]: ").strip()

        if not response and default:
            return default

        try:
            idx = int(response) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
            else:
                print(f"  Please enter a number between 1 and {len(choices)}")
        except ValueError:
            print(f"  Please enter a number between 1 and {len(choices)}")


def get_description_mapping() -> tuple:
    """
    Helper to map description field with optional reference and note.

    Returns:
        (transformations_dict, mapping_name)
    """
    print("\n" + "="*70)
    print("DESCRIPTION MAPPING HELPER")
    print("="*70)
    print("\nThis helper will create a combined description field if needed.")

    main_desc = get_input("Which column has the main description?")

    has_ref = get_yes_no("Do you have a Reference field to include?", default=False)
    ref_col = None
    if has_ref:
        ref_col = get_input("Which column contains the reference?")

    has_note = get_yes_no("Do you have a Note field to include?", default=False)
    note_col = None
    if has_note:
        note_col = get_input("Which column contains notes?")

    # Build transformation if needed
    if ref_col or note_col:
        parts = [f"'{main_desc}'"]
        if ref_col:
            parts.append(f"' [Ref: ' + '{ref_col}' + ']'")
        if note_col:
            parts.append(f"' [Note: ' + '{note_col}' + ']'")

        transformation_expr = " + ".join(parts)
        transformation_name = "combined_description"

        print(f"\n  -> Will create transformation: {transformation_name} = {transformation_expr}")

        return ({transformation_name: transformation_expr}, transformation_name)
    else:
        # No transformation needed, just direct mapping
        return ({}, main_desc)


def get_counterparty_mapping() -> tuple:
    """
    Helper to map counterparty fields.

    Returns:
        (transformations_dict, account_mapping, name_mapping)
    """
    print("\n" + "="*70)
    print("COUNTERPARTY MAPPING HELPER")
    print("="*70)
    print("\nThis helper will map counterparty information.")

    has_account = get_yes_no("Do you have counterparty account number?", default=False)
    account_col = None
    if has_account:
        account_col = get_input("Which column contains the account number?")

    has_bank = get_yes_no("Do you have counterparty bank code?", default=False)
    bank_col = None
    if has_bank:
        bank_col = get_input("Which column contains the bank code?")

    has_name = get_yes_no("Do you have counterparty name?", default=False)
    name_col = None
    if has_name:
        name_col = get_input("Which column contains the counterparty name?")

    transformations = {}
    account_mapping = None
    name_mapping = None

    # Build transformation for account+bank if both present
    if account_col and bank_col:
        transformation_expr = f"'{account_col}' + '/' + '{bank_col}'"
        transformation_name = "combined_counterparty_account"
        transformations[transformation_name] = transformation_expr
        account_mapping = transformation_name
        print(f"\n  -> Will create transformation: {transformation_name} = {transformation_expr}")
    elif account_col:
        account_mapping = account_col
        print(f"\n  -> Will map counterparty_account directly to: {account_col}")

    if name_col:
        name_mapping = name_col
        print(f"\n  -> Will map counterparty_name directly to: {name_col}")

    return (transformations, account_mapping, name_mapping)


def get_column_mappings(file_type: str, transformations: Dict[str, str] = None) -> tuple:
    """
    Get column mappings from user.

    Returns:
        (mappings_dict, helper_transformations_dict)
    """
    print("\n" + "="*70)
    print("COLUMN MAPPINGS - MAP TO STANDARD FIELDS")
    print("="*70)
    print("\nNow we'll MAP columns to standard transaction fields.")

    if transformations:
        print("\n" + "-"*70)
        print("AVAILABLE COLUMNS:")
        print("  - Original columns from your file")
        if any('+' in v for v in transformations.values()):
            print("  - Array indices (0, 1, 2...) from split data")
            print("    (Because you used structural transformations like A+B+C)")
        else:
            print("  - Transformed columns:", ", ".join(f"'{k}'" for k in transformations.keys()))
        print("-"*70)

    print("\nYou can enter:")
    print("  - Column names (e.g., 'date', 'amount', 'full_name')")
    print("  - Column numbers/indices (e.g., 0, 1, 2 - for split data)")
    print("  - Leave blank to skip optional fields")

    mappings = {}
    helper_transformations = {}

    # Required fields
    print("\n--- Required Fields ---")
    mappings['date'] = get_input("Date column")
    mappings['amount'] = get_input("Amount column")
    mappings['currency'] = get_input("Currency column", default="CZK")

    # Description with helper
    desc_trans, desc_mapping = get_description_mapping()
    mappings['description'] = desc_mapping
    helper_transformations.update(desc_trans)

    # Counterparty with helper
    cp_trans, cp_account, cp_name = get_counterparty_mapping()
    if cp_account:
        mappings['counterparty_account'] = cp_account
    if cp_name:
        mappings['counterparty_name'] = cp_name
    helper_transformations.update(cp_trans)

    # Optional fields
    print("\n--- Optional Fields ---")
    mappings['variable_symbol'] = get_input("Variable symbol column (optional)", required=False)
    mappings['transaction_type'] = get_input("Transaction type column (optional)", required=False)
    mappings['category'] = get_input("Category column (optional)", required=False)
    mappings['transaction_id'] = get_input("Transaction ID column (optional)", required=False)

    # Check if using numeric indices
    sample_key = mappings['date']
    try:
        int(sample_key)
        print("\n  Detected numeric column indices.")
        # Convert to integers
        for key, value in mappings.items():
            if value:
                try:
                    mappings[key] = int(value)
                except ValueError:
                    pass  # Keep as string if not numeric
    except ValueError:
        print("\n  Using column names.")

    return (mappings, helper_transformations)


def get_transformations() -> Dict[str, str]:
    """Get column transformations."""
    print("\n" + "="*70)
    print("TRANSFORMATIONS - CREATE NEW COLUMNS")
    print("="*70)
    print("\nTransformations allow you to CREATE NEW COLUMNS by combining or")
    print("modifying existing columns. The name you give becomes the new column header.")
    print("\n" + "-"*70)
    print("STRUCTURAL TRANSFORMATIONS (for combining columns):")
    print("  - Concatenate Excel columns: 'A' + 'B' + 'C' + 'D'")
    print("    Example: 'merged_data' = 'A' + 'B' + 'C' + 'D'")
    print("    Creates a new column called 'merged_data' with combined content")
    print("    NOTE: After this, column mapping uses ARRAY INDICES (0, 1, 2...)")
    print("\n  - Split and extract: split(';')[0]")
    print("    Splits by delimiter and takes the specified index")
    print("\nFORMAT TRANSFORMATIONS (for cleaning data):")
    print("  - Strip characters: strip('xyz')")
    print("    Example: 'currency' = strip('\"')  (removes quotes)")
    print("\n  - Replace text: replace('old', 'new')")
    print("    Example: 'amount' = replace(' ', '')  (removes spaces)")
    print("\nCOMBINING REGULAR COLUMNS:")
    print("  - Join CSV columns: 'first_name' + ' ' + 'last_name'")
    print("    Example: 'full_name' = 'first_name' + ' ' + 'last_name'")
    print("    Creates new column 'full_name' you can use in mapping")
    print("-"*70)

    if not get_yes_no("\nAdd transformations?", default=False):
        return {}

    transformations = {}
    print("\nEnter transformations (the NAME you choose becomes the column header):")
    while True:
        column = get_input("\nNew column name to create (or press Enter to finish)", required=False)
        if not column:
            break

        transform = get_input(f"Transformation expression for '{column}'")
        transformations[column] = transform
        print(f"  -> Will create column '{column}' = {transform}")

    return transformations


def get_owner_detection(institution_name: str) -> Dict[str, Any]:
    """Get owner detection configuration."""
    print("\n" + "="*70)
    print("OWNER DETECTION")
    print("="*70)
    print("\nHow should we detect the account owner?")

    method = get_choice(
        "Detection method:",
        ["fixed", "pattern", "account_number"],
        default="fixed"
    )

    config = {"method": method}

    if method == "fixed":
        owner = get_input("Owner name", default="Unknown")
        config["owner"] = owner

    elif method == "pattern":
        print("\nDefine patterns to match in description field.")
        patterns = {}
        while True:
            owner = get_input("\nOwner name (or press Enter to finish)", required=False)
            if not owner:
                break

            keywords = get_input(f"Keywords for {owner} (comma-separated)")
            patterns[owner] = [k.strip() for k in keywords.split(',')]

        config["patterns"] = patterns

    elif method == "account_number":
        print("\nMap account numbers to owners.")
        accounts = {}
        while True:
            owner = get_input("\nOwner name (or press Enter to finish)", required=False)
            if not owner:
                break

            account = get_input(f"Account number for {owner}")
            accounts[account] = owner

        config["accounts"] = accounts
        config["field"] = get_input("Account number field name", default="account_number")

    return config


def get_category_mapping() -> Optional[Dict[str, str]]:
    """Get category mapping configuration."""
    print("\n" + "="*70)
    print("CATEGORY MAPPING")
    print("="*70)

    if not get_yes_no("\nAdd custom category mappings?", default=False):
        return None

    print("\nDefine keyword patterns for categories.")
    print("Keywords will be matched against the description field.")

    mappings = {}
    while True:
        category = get_input("\nCategory name (or press Enter to finish)", required=False)
        if not category:
            break

        keywords = get_input(f"Keywords for '{category}' (comma-separated)")
        mappings[category] = [k.strip() for k in keywords.split(',')]

    return mappings if mappings else None


def create_config() -> Dict[str, Any]:
    """Create institution configuration interactively."""
    print("="*70)
    print("ADD NEW INSTITUTION CONFIGURATION")
    print("="*70)
    print("\nThis wizard will help you create a configuration file for a new")
    print("financial institution. You'll need a sample export file to reference.")
    print("\n" + "-"*70)
    print("QUICK GUIDE - Two-Step Process:")
    print("  1. TRANSFORMATIONS - CREATE new columns by combining/modifying data")
    print("     Example: Create 'full_name' from 'first_name' + 'last_name'")
    print("     The names you choose become column headers you can reference")
    print()
    print("  2. COLUMN MAPPING - MAP columns to standard field names")
    print("     Example: Map 'full_name' -> description field")
    print("     This is just assignment, not creating new columns")
    print("-"*70)
    print()

    # Basic information
    print("\n--- BASIC INFORMATION ---")
    name = get_input("Institution name (e.g., 'Raiffeisenbank', 'Wise')")
    inst_type = get_choice(
        "Institution type:",
        ["bank", "investment", "payment_platform"],
        default="bank"
    )
    country = get_input("Country code (e.g., 'CZ', 'US')", default="CZ")

    # File format
    print("\n--- FILE FORMAT ---")
    file_type = get_choice(
        "File type:",
        ["csv", "xlsx"],
        default="csv"
    )

    file_patterns = get_input(
        "Filename pattern(s) (comma-separated, e.g., 'export_*.csv, statement_*.csv')",
        default=f"{name.lower().replace(' ', '_')}_*.{file_type}"
    )
    patterns = [p.strip() for p in file_patterns.split(',')]

    # Format-specific settings
    format_config = {}

    if file_type == 'csv':
        print("\n--- CSV FORMAT ---")
        encoding = get_choice(
            "File encoding:",
            ["utf-8", "utf-8-sig", "windows-1250", "iso-8859-1"],
            default="utf-8"
        )

        delimiter = get_input("Delimiter", default=",")
        # Handle special cases
        if delimiter.lower() in ['semicolon', ';']:
            delimiter = ';'
        elif delimiter.lower() in ['tab', '\\t']:
            delimiter = '\t'

        has_header = get_yes_no("Does CSV have a header row?", default=True)

        skip_rows = 0
        if get_yes_no("Skip rows at the beginning?", default=False):
            skip_rows = int(get_input("Number of rows to skip", default="0"))

        format_config = {
            'encoding': encoding,
            'delimiter': delimiter,
            'has_header': has_header,
            'skip_rows': skip_rows
        }

    elif file_type == 'xlsx':
        print("\n--- XLSX FORMAT ---")
        sheet_name = get_input("Sheet name (or press Enter for first sheet)", required=False)
        if sheet_name:
            format_config['sheet_name'] = sheet_name

        skip_rows = 0
        if get_yes_no("Skip rows at the beginning?", default=False):
            skip_rows = int(get_input("Number of rows to skip", default="0"))
            format_config['skip_rows'] = skip_rows

    # Transformations (get this first!)
    transformations = get_transformations()

    # Show what was created
    if transformations:
        print("\n" + "="*70)
        print("TRANSFORMATION SUMMARY")
        print("="*70)
        print("Created the following new columns:")
        for col_name, expr in transformations.items():
            print(f"  - '{col_name}' = {expr}")
        print("\nYou can now use these column names in the mapping step.")
        print("="*70)

    # Column mappings (now we can reference transformed columns)
    # Returns: (mappings, helper_transformations)
    columns, helper_transformations = get_column_mappings(file_type, transformations)

    # Date format
    print("\n--- DATE FORMAT ---")
    print("Examples: '%d.%m.%Y', '%Y-%m-%d %H:%M:%S', '%d. %m. %Y'")
    date_format = get_input("Date format", default="%d.%m.%Y")

    # Amount format
    print("\n--- AMOUNT FORMAT ---")
    decimal_sep = get_input("Decimal separator", default=",")
    thousands_sep = get_input("Thousands separator (or press Enter for none)", required=False)

    amount_format = {
        'decimal_separator': decimal_sep
    }
    if thousands_sep:
        amount_format['thousands_separator'] = thousands_sep

    # Owner detection
    owner_config = get_owner_detection(name)

    # Category mapping
    category_mapping = get_category_mapping()

    # Build final config
    config = {
        'institution': {
            'name': name,
            'type': inst_type,
            'country': country
        },
        'file_detection': {
            'filename_patterns': patterns
        },
        'csv_format': {
            **format_config
        },
        'column_mapping': columns,
        'owner_detection': owner_config
    }

    # Build transformations section
    trans_section = {}

    # Add date transformation
    if date_format:
        trans_section['date'] = {'format': date_format}

    # Add amount transformation
    if amount_format:
        trans_section['amount'] = amount_format

    # Add helper transformations (from description/counterparty helpers)
    if helper_transformations:
        for key, value in helper_transformations.items():
            trans_section[key] = value

    # Add custom transformations (like A+B+C)
    if transformations:
        # Merge with custom transformations
        for key, value in transformations.items():
            trans_section[key] = value

    if trans_section:
        config['transformations'] = trans_section

    if category_mapping:
        config['category_mapping'] = category_mapping

    return config


def save_config(config: Dict[str, Any]) -> bool:
    """Save configuration to YAML file."""
    config_dir = Path("config/institutions")
    config_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    inst_name = config['institution']['name']
    filename = f"{inst_name.lower().replace(' ', '_')}.yaml"
    filepath = config_dir / filename

    # Check if exists
    if filepath.exists():
        print(f"\n⚠️  Warning: {filepath} already exists!")
        if not get_yes_no("Overwrite?", default=False):
            print("  Cancelled.")
            return False

    # Save
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        print(f"\n✅ Configuration saved to: {filepath}")
        return True

    except Exception as e:
        print(f"\n❌ Failed to save configuration: {str(e)}")
        return False


def show_config_preview(config: Dict[str, Any]):
    """Show preview of configuration."""
    print("\n" + "="*70)
    print("CONFIGURATION PREVIEW")
    print("="*70)
    print()
    print(yaml.dump(config, default_flow_style=False, allow_unicode=True, sort_keys=False))
    print("="*70)


def main():
    """Main entry point."""
    try:
        # Create config
        config = create_config()

        # Show preview
        show_config_preview(config)

        # Confirm and save
        if get_yes_no("\nSave this configuration?", default=True):
            if save_config(config):
                print("\n" + "="*70)
                print("NEXT STEPS")
                print("="*70)
                print("\n1. Test your configuration with a sample file:")
                inst_name = config['institution']['name']
                print(f"   python scripts/test_config.py --institution \"{inst_name}\" --file <path-to-sample-file>")
                print("\n2. If the test looks good, your institution is ready to use!")
                print()
        else:
            print("\nConfiguration not saved.")

    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
