"""Category Management API"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
import logging
import yaml
from pathlib import Path

from backend.schemas.categories import (
    CategoryTree,
    Tier1Category,
    Tier2Category,
    Tier3Category,
    CategoryCreate,
    CategoryUpdate
)

logger = logging.getLogger(__name__)

router = APIRouter()


def load_categories_from_sheets():
    """Load categories from Google Sheets"""
    try:
        from src.utils.categorizer import TransactionCategorizer

        # Create categorizer instance to load categories
        categorizer = TransactionCategorizer(
            config_path="config/categorization.yaml",
            settings_path="config/settings.yaml"
        )

        return categorizer.category_tree
    except Exception as e:
        logger.error(f"Error loading categories from Google Sheets: {e}")
        return []


def save_categories_to_sheets(categories: List[Dict]):
    """Save categories back to Google Sheets"""
    try:
        from src.connectors.google_sheets import GoogleSheetsConnector
        import yaml

        # Load settings
        with open("config/settings.yaml", 'r', encoding='utf-8') as f:
            settings = yaml.safe_load(f)

        cat_config = settings.get('categorization', {})
        sheets_config = cat_config.get('google_sheets', {})
        spreadsheet_id = sheets_config.get('spreadsheet_id',
                                          settings.get('google_sheets', {}).get('master_sheet_id'))
        categories_tab = sheets_config.get('categories_tab', 'Categories')

        # Get credentials
        creds_path = settings.get('google_drive', {}).get('credentials_path')
        token_path = settings.get('google_drive', {}).get('token_path')

        # Connect to Google Sheets
        connector = GoogleSheetsConnector(creds_path, token_path)
        if not connector.authenticate():
            raise Exception("Failed to authenticate with Google Sheets")

        # Convert categories to rows format
        rows = [['Tier1', 'Tier2', 'Tier3']]  # Header row

        for tier1_cat in categories:
            tier1 = tier1_cat.get('tier1')
            tier2_categories = tier1_cat.get('tier2_categories', [])

            # If tier1 has no tier2 children, write it with empty tier2/tier3
            if not tier2_categories:
                rows.append([tier1, '', ''])
            else:
                for tier2_cat in tier2_categories:
                    tier2 = tier2_cat.get('tier2')
                    tier3_list = tier2_cat.get('tier3', [])

                    # If tier2 has no tier3 children, write it with empty tier3
                    if not tier3_list:
                        rows.append([tier1, tier2, ''])
                    else:
                        for tier3 in tier3_list:
                            rows.append([tier1, tier2, tier3])

        # Write to sheet (overwrites by default)
        connector.write_sheet(
            spreadsheet_id,
            f"{categories_tab}!A1",
            rows
        )

        return True
    except Exception as e:
        logger.error(f"Error saving categories to Google Sheets: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@router.get("/tree", response_model=List[Tier1Category])
async def get_category_tree():
    """Get complete 3-tier category tree"""
    try:
        categories = load_categories_from_sheets()
        return categories
    except Exception as e:
        logger.error(f"Error fetching category tree: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tier1", response_model=List[str])
async def get_tier1_categories():
    """Get list of tier1 categories"""
    try:
        categories = load_categories_from_sheets()
        return [cat['tier1'] for cat in categories]
    except Exception as e:
        logger.error(f"Error fetching tier1 categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tier2/{tier1}", response_model=List[str])
async def get_tier2_categories(tier1: str):
    """Get tier2 categories for a specific tier1"""
    try:
        categories = load_categories_from_sheets()
        for cat in categories:
            if cat['tier1'] == tier1:
                return [t2['tier2'] for t2 in cat.get('tier2_categories', [])]
        return []
    except Exception as e:
        logger.error(f"Error fetching tier2 categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tier3/{tier1}/{tier2}", response_model=List[str])
async def get_tier3_categories(tier1: str, tier2: str):
    """Get tier3 categories for a specific tier1/tier2"""
    try:
        categories = load_categories_from_sheets()
        for cat in categories:
            if cat['tier1'] == tier1:
                for t2 in cat.get('tier2_categories', []):
                    if t2['tier2'] == tier2:
                        return t2.get('tier3', [])
        return []
    except Exception as e:
        logger.error(f"Error fetching tier3 categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tier1")
async def create_tier1_category(name: str):
    """Create a new tier1 category"""
    try:
        categories = load_categories_from_sheets()

        # Check if already exists
        if any(cat['tier1'] == name for cat in categories):
            raise HTTPException(status_code=400, detail="Category already exists")

        # Add new tier1
        categories.append({
            'tier1': name,
            'tier2_categories': []
        })

        # Save back to sheets
        save_categories_to_sheets(categories)

        return {'message': 'Tier1 category created successfully', 'name': name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tier1 category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tier2/{tier1}")
async def create_tier2_category(tier1: str, name: str):
    """Create a new tier2 category under a tier1"""
    try:
        categories = load_categories_from_sheets()

        # Find tier1
        tier1_cat = None
        for cat in categories:
            if cat['tier1'] == tier1:
                tier1_cat = cat
                break

        if not tier1_cat:
            raise HTTPException(status_code=404, detail="Tier1 category not found")

        # Check if tier2 already exists
        tier2_categories = tier1_cat.get('tier2_categories', [])
        if any(t2['tier2'] == name for t2 in tier2_categories):
            raise HTTPException(status_code=400, detail="Tier2 category already exists")

        # Add new tier2
        tier2_categories.append({
            'tier2': name,
            'tier3': []
        })

        # Save back to sheets
        save_categories_to_sheets(categories)

        return {'message': 'Tier2 category created successfully', 'name': name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tier2 category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tier3/{tier1}/{tier2}")
async def create_tier3_category(tier1: str, tier2: str, name: str):
    """Create a new tier3 category"""
    try:
        categories = load_categories_from_sheets()

        # Find tier1 and tier2
        tier2_cat = None
        for cat in categories:
            if cat['tier1'] == tier1:
                for t2 in cat.get('tier2_categories', []):
                    if t2['tier2'] == tier2:
                        tier2_cat = t2
                        break
                break

        if not tier2_cat:
            raise HTTPException(status_code=404, detail="Tier2 category not found")

        # Check if tier3 already exists
        tier3_list = tier2_cat.get('tier3', [])
        if name in tier3_list:
            raise HTTPException(status_code=400, detail="Tier3 category already exists")

        # Add new tier3
        tier3_list.append(name)

        # Save back to sheets
        save_categories_to_sheets(categories)

        return {'message': 'Tier3 category created successfully', 'name': name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tier3 category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tier1/{tier1}")
async def delete_tier1_category(tier1: str):
    """Delete a tier1 category (and all its children)"""
    try:
        categories = load_categories_from_sheets()

        # Remove tier1
        categories = [cat for cat in categories if cat['tier1'] != tier1]

        # Save back to sheets
        save_categories_to_sheets(categories)

        return {'message': 'Tier1 category deleted successfully'}
    except Exception as e:
        logger.error(f"Error deleting tier1 category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tier2/{tier1}/{tier2}")
async def delete_tier2_category(tier1: str, tier2: str):
    """Delete a tier2 category (and all its children)"""
    try:
        categories = load_categories_from_sheets()

        # Find and remove tier2
        for cat in categories:
            if cat['tier1'] == tier1:
                cat['tier2_categories'] = [
                    t2 for t2 in cat.get('tier2_categories', [])
                    if t2['tier2'] != tier2
                ]
                break

        # Save back to sheets
        save_categories_to_sheets(categories)

        return {'message': 'Tier2 category deleted successfully'}
    except Exception as e:
        logger.error(f"Error deleting tier2 category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tier3/{tier1}/{tier2}/{tier3}")
async def delete_tier3_category(tier1: str, tier2: str, tier3: str):
    """Delete a tier3 category"""
    try:
        categories = load_categories_from_sheets()

        # Find and remove tier3
        for cat in categories:
            if cat['tier1'] == tier1:
                for t2 in cat.get('tier2_categories', []):
                    if t2['tier2'] == tier2:
                        tier3_list = t2.get('tier3', [])
                        if tier3 in tier3_list:
                            tier3_list.remove(tier3)
                        break
                break

        # Save back to sheets
        save_categories_to_sheets(categories)

        return {'message': 'Tier3 category deleted successfully'}
    except Exception as e:
        logger.error(f"Error deleting tier3 category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tier1/{old_name}")
async def rename_tier1_category(old_name: str, new_name: str):
    """Rename a tier1 category"""
    try:
        categories = load_categories_from_sheets()

        # Find and rename
        found = False
        for cat in categories:
            if cat['tier1'] == old_name:
                cat['tier1'] = new_name
                found = True
                break

        if not found:
            raise HTTPException(status_code=404, detail="Category not found")

        # Save back to sheets
        save_categories_to_sheets(categories)

        return {'message': 'Tier1 category renamed successfully'}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error renaming tier1 category: {e}")
        raise HTTPException(status_code=500, detail=str(e))
