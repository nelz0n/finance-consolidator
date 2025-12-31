"""Settings API endpoints"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel
import yaml
from pathlib import Path
import re

router = APIRouter()


# Pydantic models for request/response
class InstitutionCreate(BaseModel):
    name: str
    type: str = "bank"
    country: str = "CZ"
    filename_patterns: List[str]
    encoding: str = "utf-8-sig"
    delimiter: str = ";"
    has_header: bool = True
    skip_rows: int = 0
    date_format: str = "%d.%m.%Y"
    decimal_separator: str = ","
    thousands_separator: str = " "
    reverse_sign: bool = False
    column_mapping: Dict[str, str]
    custom_transformations: Dict[str, str] = {}
    defaults: Dict[str, str] = {}  # Default values for fields (e.g., account: extract_from_filename)
    skip_patterns: List[str] = []  # Patterns to skip rows (filtering.skip_if_contains)
    owner_mappings: Dict[str, str] = {}


class InstitutionUpdate(BaseModel):
    name: str = None
    type: str = None
    country: str = None
    filename_patterns: List[str] = None
    encoding: str = None
    delimiter: str = None
    has_header: bool = None
    skip_rows: int = None
    date_format: str = None
    decimal_separator: str = None
    thousands_separator: str = None
    reverse_sign: bool = None
    column_mapping: Dict[str, str] = None
    custom_transformations: Dict[str, str] = None
    defaults: Dict[str, str] = None
    skip_patterns: List[str] = None
    owner_mappings: Dict[str, str] = None


class OwnerAccount(BaseModel):
    account: str
    institution: str


class Owner(BaseModel):
    name: str
    accounts: List[OwnerAccount]


@router.get("/app")
async def get_app_settings():
    """Get application settings"""
    try:
        settings_path = Path("config/settings.yaml")
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = yaml.safe_load(f)

        # Return user-editable settings
        return {
            "currency": {
                "base_currency": settings['currency']['base_currency'],
                "use_cnb_api": settings['currency']['use_cnb_api'],
                "supported": settings['currency']['supported'],
                "rates": settings['currency']['rates']
            },
            "processing": {
                "timezone": settings['processing']['timezone']
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/app")
async def update_app_settings(updates: Dict[str, Any]):
    """Update application settings"""
    try:
        settings_path = Path("config/settings.yaml")

        # Read current settings
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = yaml.safe_load(f)

        # Update settings
        if "currency" in updates:
            settings['currency'].update(updates['currency'])
        if "processing" in updates:
            settings['processing'].update(updates['processing'])

        # Write back to file
        with open(settings_path, 'w', encoding='utf-8') as f:
            yaml.dump(settings, f, default_flow_style=False, allow_unicode=True)

        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/institutions")
async def get_institutions():
    """Get all institution configurations"""
    try:
        institutions_dir = Path("config/institutions")
        institutions = []

        for yaml_file in institutions_dir.glob("*.yaml"):
            with open(yaml_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

                institutions.append({
                    "id": yaml_file.stem,
                    "name": config['institution']['name'],
                    "type": config['institution']['type'],
                    "country": config['institution'].get('country', 'Unknown'),
                    "enabled": True,  # We can add this to config later
                    "owner_mappings": config.get('owner_detection', {}).get('account_mapping', {})
                })

        return {"institutions": institutions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/institutions/{institution_id}")
async def get_institution(institution_id: str):
    """Get specific institution configuration"""
    try:
        institution_path = Path(f"config/institutions/{institution_id}.yaml")

        if not institution_path.exists():
            raise HTTPException(status_code=404, detail="Institution not found")

        with open(institution_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        return config
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/institutions/{institution_id}/owners")
async def update_institution_owners(institution_id: str, owner_mappings: Dict[str, str]):
    """Update owner mappings for an institution"""
    try:
        institution_path = Path(f"config/institutions/{institution_id}.yaml")

        if not institution_path.exists():
            raise HTTPException(status_code=404, detail="Institution not found")

        # Read current config
        with open(institution_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Update owner mappings
        if 'owner_detection' not in config:
            config['owner_detection'] = {}
        if 'account_mapping' not in config['owner_detection']:
            config['owner_detection']['account_mapping'] = {}

        config['owner_detection']['account_mapping'] = owner_mappings

        # Write back
        with open(institution_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        return {"status": "updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/institutions")
async def create_institution(institution: InstitutionCreate):
    """Create a new institution configuration"""
    try:
        # Generate ID from name (lowercase, replace spaces with underscores)
        institution_id = re.sub(r'[^a-z0-9_]', '', institution.name.lower().replace(' ', '_'))
        institution_path = Path(f"config/institutions/{institution_id}.yaml")

        # Check if already exists
        if institution_path.exists():
            raise HTTPException(status_code=400, detail=f"Institution '{institution_id}' already exists")

        # Build config structure
        config = {
            "institution": {
                "name": institution.name,
                "type": institution.type,
                "country": institution.country
            },
            "file_detection": {
                "filename_patterns": institution.filename_patterns
            },
            "csv_format": {
                "encoding": institution.encoding,
                "delimiter": institution.delimiter,
                "has_header": institution.has_header,
                "skip_rows": institution.skip_rows
            },
            "transformations": {
                "date": {
                    "format": institution.date_format
                },
                "amount": {
                    "decimal_separator": institution.decimal_separator,
                    "thousands_separator": institution.thousands_separator,
                    "reverse_sign": institution.reverse_sign
                },
                **institution.custom_transformations  # Add custom transformations
            },
            "column_mapping": institution.column_mapping,
            "owner_detection": {
                "method": "account_mapping",
                "account_mapping": institution.owner_mappings,
                "default_owner": "Unknown"
            }
        }

        # Add defaults to column_mapping if provided
        if institution.defaults:
            config["column_mapping"]["defaults"] = institution.defaults

        # Add filtering if skip_patterns provided
        if institution.skip_patterns:
            config["filtering"] = {
                "skip_if_contains": institution.skip_patterns
            }

        # Write to file
        with open(institution_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        return {
            "status": "created",
            "institution_id": institution_id,
            "message": f"Institution '{institution.name}' created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/institutions/{institution_id}")
async def update_institution(institution_id: str, updates: InstitutionUpdate):
    """Update an existing institution configuration"""
    try:
        institution_path = Path(f"config/institutions/{institution_id}.yaml")

        if not institution_path.exists():
            raise HTTPException(status_code=404, detail="Institution not found")

        # Read current config
        with open(institution_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Update fields if provided
        if updates.name is not None:
            config['institution']['name'] = updates.name
        if updates.type is not None:
            config['institution']['type'] = updates.type
        if updates.country is not None:
            config['institution']['country'] = updates.country
        if updates.filename_patterns is not None:
            config['file_detection']['filename_patterns'] = updates.filename_patterns
        if updates.encoding is not None:
            config['csv_format']['encoding'] = updates.encoding
        if updates.delimiter is not None:
            config['csv_format']['delimiter'] = updates.delimiter
        if updates.has_header is not None:
            config['csv_format']['has_header'] = updates.has_header
        if updates.skip_rows is not None:
            config['csv_format']['skip_rows'] = updates.skip_rows
        if updates.date_format is not None:
            config['transformations']['date']['format'] = updates.date_format
        if updates.decimal_separator is not None:
            config['transformations']['amount']['decimal_separator'] = updates.decimal_separator
        if updates.thousands_separator is not None:
            config['transformations']['amount']['thousands_separator'] = updates.thousands_separator
        if updates.reverse_sign is not None:
            config['transformations']['amount']['reverse_sign'] = updates.reverse_sign
        if updates.column_mapping is not None:
            config['column_mapping'] = updates.column_mapping
        if updates.defaults is not None:
            # Add or update defaults in column_mapping
            if 'column_mapping' not in config:
                config['column_mapping'] = {}
            if updates.defaults:
                config['column_mapping']['defaults'] = updates.defaults
            elif 'defaults' in config.get('column_mapping', {}):
                # Remove defaults if empty dict passed
                del config['column_mapping']['defaults']
        if updates.skip_patterns is not None:
            # Add or update filtering
            if updates.skip_patterns:
                config['filtering'] = {'skip_if_contains': updates.skip_patterns}
            elif 'filtering' in config:
                # Remove filtering if empty list passed
                del config['filtering']
        if updates.custom_transformations is not None:
            # Merge custom transformations into existing transformations
            if 'transformations' not in config:
                config['transformations'] = {}
            # Remove old custom transformations (keep only date and amount)
            keys_to_keep = ['date', 'amount']
            config['transformations'] = {k: v for k, v in config['transformations'].items() if k in keys_to_keep}
            # Add new custom transformations
            config['transformations'].update(updates.custom_transformations)
        if updates.owner_mappings is not None:
            if 'owner_detection' not in config:
                config['owner_detection'] = {"method": "account_mapping", "default_owner": "Unknown"}
            config['owner_detection']['account_mapping'] = updates.owner_mappings

        # Write back
        with open(institution_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        return {"status": "updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/institutions/{institution_id}")
async def delete_institution(institution_id: str):
    """Delete an institution configuration"""
    try:
        institution_path = Path(f"config/institutions/{institution_id}.yaml")

        if not institution_path.exists():
            raise HTTPException(status_code=404, detail="Institution not found")

        # Delete the file
        institution_path.unlink()

        return {
            "status": "deleted",
            "message": f"Institution '{institution_id}' deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/owners")
async def get_all_owners():
    """Get all unique owners across all institutions"""
    try:
        institutions_dir = Path("config/institutions")
        owners_dict = {}  # owner_name -> list of {account, institution}

        for yaml_file in institutions_dir.glob("*.yaml"):
            with open(yaml_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                institution_name = config['institution']['name']
                account_mapping = config.get('owner_detection', {}).get('account_mapping', {})

                for account, owner in account_mapping.items():
                    if owner not in owners_dict:
                        owners_dict[owner] = []
                    owners_dict[owner].append({
                        "account": account,
                        "institution": institution_name,
                        "institution_id": yaml_file.stem
                    })

        # Convert to list format
        owners = [
            {
                "name": owner_name,
                "accounts": accounts
            }
            for owner_name, accounts in sorted(owners_dict.items())
        ]

        return {"owners": owners}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/owners/{owner_name}/accounts")
async def add_owner_account(owner_name: str, account: str, institution_id: str):
    """Add an account to an owner in a specific institution"""
    try:
        institution_path = Path(f"config/institutions/{institution_id}.yaml")

        if not institution_path.exists():
            raise HTTPException(status_code=404, detail="Institution not found")

        # Read current config
        with open(institution_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Initialize owner_detection if needed
        if 'owner_detection' not in config:
            config['owner_detection'] = {
                "method": "account_mapping",
                "account_mapping": {},
                "default_owner": "Unknown"
            }
        if 'account_mapping' not in config['owner_detection']:
            config['owner_detection']['account_mapping'] = {}

        # Add the account mapping
        config['owner_detection']['account_mapping'][account] = owner_name

        # Write back
        with open(institution_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        return {"status": "added"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/owners/{owner_name}/accounts")
async def remove_owner_account(owner_name: str, account: str, institution_id: str):
    """Remove an account from an owner in a specific institution"""
    try:
        institution_path = Path(f"config/institutions/{institution_id}.yaml")

        if not institution_path.exists():
            raise HTTPException(status_code=404, detail="Institution not found")

        # Read current config
        with open(institution_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Remove the account mapping
        account_mapping = config.get('owner_detection', {}).get('account_mapping', {})
        if account in account_mapping and account_mapping[account] == owner_name:
            del account_mapping[account]

            # Write back
            with open(institution_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            return {"status": "removed"}
        else:
            raise HTTPException(status_code=404, detail="Account mapping not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
