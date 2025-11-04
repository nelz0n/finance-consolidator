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


def get_column_mappings(file_type: str) -> Dict[str, Any]:
    """Get column mappings from user."""
    print("\n" + "="*70)
    print("COLUMN MAPPINGS")
    print("="*70)
    print("\nNow we'll map the columns from your file to standard fields.")
    print("You can enter:")
    print("  - Column names (for CSV with headers or XLSX)")
    print("  - Column numbers/indices (for CSV without headers)")
    print("  - Leave blank to skip optional fields")

    mappings = {}

    # Required fields
    print("\n--- Required Fields ---")
    mappings['date'] = get_input("Date column")
    mappings['amount'] = get_input("Amount column")
    mappings['currency'] = get_input("Currency column", default="CZK")
    mappings['description'] = get_input("Description column")

    # Optional fields
    print("\n--- Optional Fields ---")
    mappings['category'] = get_input("Category column (optional)", required=False)
    mappings['transaction_id'] = get_input("Transaction ID column (optional)", required=False)
    mappings['balance'] = get_input("Balance column (optional)", required=False)

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

    return mappings


def get_transformations() -> Dict[str, str]:
    """Get column transformations."""
    print("\n" + "="*70)
    print("TRANSFORMATIONS")
    print("="*70)
    print("\nDo you need any column transformations?")
    print("Examples:")
    print("  - Concatenate columns: 'A' + 'B' + 'C' + 'D'")
    print("  - Strip text: strip('xyz')")
    print("  - Replace text: replace('old', 'new')")

    if not get_yes_no("\nAdd transformations?", default=False):
        return {}

    transformations = {}
    while True:
        column = get_input("\nColumn to transform (or press Enter to finish)", required=False)
        if not column:
            break

        transform = get_input(f"Transformation for '{column}'")
        transformations[column] = transform

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
    print()

    # Basic information
    print("\n--- BASIC INFORMATION ---")
    name = get_input("Institution name (e.g., 'ČSOB', 'Wise')")
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

    # Column mappings
    columns = get_column_mappings(file_type)

    # Transformations
    transformations = get_transformations()

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
        'file_patterns': patterns,
        'format': {
            'type': file_type,
            **format_config
        },
        'columns': columns,
        'date_format': date_format,
        'amount_format': amount_format,
        'owner_detection': owner_config
    }

    if transformations:
        config['transformations'] = transformations

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
