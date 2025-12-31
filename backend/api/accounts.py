"""Accounts Management API - Manage accounts.yaml configuration"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Optional
from pydantic import BaseModel
import yaml
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class AccountConfig(BaseModel):
    description: str


class AccountsConfig(BaseModel):
    accounts: Dict[str, AccountConfig]


@router.get("/accounts")
async def get_accounts():
    """Get all accounts from accounts.yaml"""
    try:
        accounts_path = Path("config/accounts.yaml")
        if not accounts_path.exists():
            return {"accounts": {}}

        with open(accounts_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return config or {"accounts": {}}
    except Exception as e:
        logger.error(f"Error loading accounts.yaml: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts")
async def save_accounts(config: AccountsConfig):
    """Save accounts to accounts.yaml"""
    try:
        accounts_path = Path("config/accounts.yaml")

        # Prepare YAML content with comments
        yaml_content = """# Central account mapping
# Maps account numbers to friendly descriptions
# Institution is determined from upload context
# Owner is managed via Settings UI

accounts:
"""

        # Sort accounts by account number for readability
        sorted_accounts = sorted(config.accounts.items())

        for account_number, account_config in sorted_accounts:
            yaml_content += f'  "{account_number}":\n'
            yaml_content += f'    description: "{account_config.description}"\n'

        # Write to file
        with open(accounts_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)

        logger.info(f"Saved {len(config.accounts)} accounts to accounts.yaml")
        return {"message": "Accounts saved successfully", "count": len(config.accounts)}
    except Exception as e:
        logger.error(f"Error saving accounts.yaml: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/accounts/{account_number}")
async def update_account(account_number: str, account: AccountConfig):
    """Update a single account"""
    try:
        accounts_path = Path("config/accounts.yaml")

        # Load existing config
        if accounts_path.exists():
            with open(accounts_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {"accounts": {}}
        else:
            config = {"accounts": {}}

        # Update account
        config["accounts"][account_number] = {"description": account.description}

        # Save back
        accounts_config = AccountsConfig(accounts=config["accounts"])
        return await save_accounts(accounts_config)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/accounts/{account_number}")
async def delete_account(account_number: str):
    """Delete an account"""
    try:
        accounts_path = Path("config/accounts.yaml")

        if not accounts_path.exists():
            raise HTTPException(status_code=404, detail="accounts.yaml not found")

        # Load existing config
        with open(accounts_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {"accounts": {}}

        # Check if account exists
        if account_number not in config.get("accounts", {}):
            raise HTTPException(status_code=404, detail="Account not found")

        # Delete account
        del config["accounts"][account_number]

        # Save back
        accounts_config = AccountsConfig(accounts=config["accounts"])
        await save_accounts(accounts_config)

        return {"message": "Account deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting account: {e}")
        raise HTTPException(status_code=500, detail=str(e))
