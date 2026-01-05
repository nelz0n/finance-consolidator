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


def load_categories_from_database():
    """Load categories from SQLite database"""
    try:
        from backend.database.connection import get_db_context
        from backend.database.models import Category

        with get_db_context() as db:
            # Get all categories
            db_categories = db.query(Category).all()

            # Build hierarchical structure: tier1 -> tier2 -> [tier3]
            category_tree = {}

            for cat in db_categories:
                tier1 = cat.tier1
                tier2 = cat.tier2 or ""
                tier3 = cat.tier3 or ""

                # Initialize tier1 if not exists
                if tier1 not in category_tree:
                    category_tree[tier1] = {}

                # Add tier2 if it exists
                if tier2:
                    if tier2 not in category_tree[tier1]:
                        category_tree[tier1][tier2] = []

                    # Add tier3 if it exists and not duplicate
                    if tier3 and tier3 not in category_tree[tier1][tier2]:
                        category_tree[tier1][tier2].append(tier3)

            # Convert to expected list format
            result = []
            for tier1, tier2_dict in category_tree.items():
                tier2_categories = []
                for tier2, tier3_list in tier2_dict.items():
                    tier2_categories.append({
                        'tier2': tier2,
                        'tier3': tier3_list
                    })

                result.append({
                    'tier1': tier1,
                    'tier2_categories': tier2_categories
                })

            logger.info(f"Loaded category tree from database: {len(result)} tier1 categories")
            return result

    except Exception as e:
        logger.error(f"Error loading categories from database: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


@router.get("/tree", response_model=List[Tier1Category])
async def get_category_tree():
    """Get complete 3-tier category tree"""
    try:
        categories = load_categories_from_database()
        return categories
    except Exception as e:
        logger.error(f"Error fetching category tree: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tier1", response_model=List[str])
async def get_tier1_categories():
    """Get list of tier1 categories"""
    try:
        categories = load_categories_from_database()
        return [cat['tier1'] for cat in categories]
    except Exception as e:
        logger.error(f"Error fetching tier1 categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tier2/{tier1}", response_model=List[str])
async def get_tier2_categories(tier1: str):
    """Get tier2 categories for a specific tier1"""
    try:
        categories = load_categories_from_database()
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
        categories = load_categories_from_database()
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
        from backend.database.connection import get_db_context
        from backend.database.models import Category

        with get_db_context() as db:
            # Check if already exists
            existing = db.query(Category).filter(Category.tier1 == name, Category.tier2 == None).first()
            if existing:
                raise HTTPException(status_code=400, detail="Category already exists")

            # Create new tier1 category (with empty tier2 and tier3)
            new_category = Category(
                tier1=name,
                tier2=None,
                tier3=None
            )
            db.add(new_category)
            db.commit()

            logger.info(f"Created tier1 category: {name}")
            return {'message': 'Tier1 category created successfully', 'name': name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tier1 category: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tier2/{tier1}")
async def create_tier2_category(tier1: str, name: str):
    """Create a new tier2 category under a tier1"""
    try:
        from backend.database.connection import get_db_context
        from backend.database.models import Category

        with get_db_context() as db:
            # Check if tier1 exists
            tier1_exists = db.query(Category).filter(Category.tier1 == tier1).first()
            if not tier1_exists:
                raise HTTPException(status_code=404, detail="Tier1 category not found")

            # Check if tier2 already exists
            existing = db.query(Category).filter(
                Category.tier1 == tier1,
                Category.tier2 == name,
                Category.tier3 == None
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="Tier2 category already exists")

            # Create new tier2 category
            new_category = Category(
                tier1=tier1,
                tier2=name,
                tier3=None
            )
            db.add(new_category)
            db.commit()

            logger.info(f"Created tier2 category: {tier1} > {name}")
            return {'message': 'Tier2 category created successfully', 'name': name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tier2 category: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tier3/{tier1}/{tier2}")
async def create_tier3_category(tier1: str, tier2: str, name: str):
    """Create a new tier3 category"""
    try:
        from backend.database.connection import get_db_context
        from backend.database.models import Category

        with get_db_context() as db:
            # Check if tier2 exists
            tier2_exists = db.query(Category).filter(
                Category.tier1 == tier1,
                Category.tier2 == tier2
            ).first()
            if not tier2_exists:
                raise HTTPException(status_code=404, detail="Tier2 category not found")

            # Check if tier3 already exists
            existing = db.query(Category).filter(
                Category.tier1 == tier1,
                Category.tier2 == tier2,
                Category.tier3 == name
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="Tier3 category already exists")

            # Create new tier3 category
            new_category = Category(
                tier1=tier1,
                tier2=tier2,
                tier3=name
            )
            db.add(new_category)
            db.commit()

            logger.info(f"Created tier3 category: {tier1} > {tier2} > {name}")
            return {'message': 'Tier3 category created successfully', 'name': name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tier3 category: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tier1/{tier1}")
async def delete_tier1_category(tier1: str):
    """Delete a tier1 category (and all its children)"""
    try:
        categories = load_categories_from_database()

        # Remove tier1
        categories = [cat for cat in categories if cat['tier1'] != tier1]

        return {'message': 'Tier1 category deleted successfully'}
    except Exception as e:
        logger.error(f"Error deleting tier1 category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tier2/{tier1}/{tier2}")
async def delete_tier2_category(tier1: str, tier2: str):
    """Delete a tier2 category (and all its children)"""
    try:
        categories = load_categories_from_database()

        # Find and remove tier2
        for cat in categories:
            if cat['tier1'] == tier1:
                cat['tier2_categories'] = [
                    t2 for t2 in cat.get('tier2_categories', [])
                    if t2['tier2'] != tier2
                ]
                break

        return {'message': 'Tier2 category deleted successfully'}
    except Exception as e:
        logger.error(f"Error deleting tier2 category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tier3/{tier1}/{tier2}/{tier3}")
async def delete_tier3_category(tier1: str, tier2: str, tier3: str):
    """Delete a tier3 category"""
    try:
        categories = load_categories_from_database()

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

        return {'message': 'Tier3 category deleted successfully'}
    except Exception as e:
        logger.error(f"Error deleting tier3 category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tier1/{old_name}")
async def rename_tier1_category(old_name: str, new_name: str):
    """
    Rename a tier1 category and cascade to all transactions and rules.

    Updates:
    - Category table entries (all rows with tier1=old_name)
    - Transaction.category_tier1 where it matches old_name
    - CategorizationRule.category_tier1 where it matches old_name
    """
    try:
        from backend.database.connection import get_db_context
        from backend.database.models import Category, Transaction, CategorizationRule

        with get_db_context() as db:
            # 1. Validate: Check if new_name would create duplicate
            duplicate = db.query(Category).filter(
                Category.tier1 == new_name
            ).first()
            if duplicate:
                raise HTTPException(
                    status_code=400,
                    detail=f"Category '{new_name}' already exists"
                )

            # 2. Check if old_name exists
            existing = db.query(Category).filter(
                Category.tier1 == old_name
            ).first()
            if not existing:
                raise HTTPException(
                    status_code=404,
                    detail=f"Category '{old_name}' not found"
                )

            # 3. Update Category table (all entries with this tier1)
            db.query(Category).filter(
                Category.tier1 == old_name
            ).update(
                {Category.tier1: new_name},
                synchronize_session=False
            )

            # 4. CASCADE: Update all transactions
            txn_count = db.query(Transaction).filter(
                Transaction.category_tier1 == old_name
            ).update(
                {Transaction.category_tier1: new_name},
                synchronize_session=False
            )

            # 5. CASCADE: Update all rules
            rule_count = db.query(CategorizationRule).filter(
                CategorizationRule.category_tier1 == old_name
            ).update(
                {CategorizationRule.category_tier1: new_name},
                synchronize_session=False
            )

            db.commit()

            logger.info(
                f"Renamed tier1 '{old_name}' -> '{new_name}': "
                f"{txn_count} transactions, {rule_count} rules updated"
            )

            return {
                'message': 'Tier1 category renamed successfully',
                'updated': {
                    'transactions': txn_count,
                    'rules': rule_count
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error renaming tier1 category: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tier2/{tier1}/{old_name}")
async def rename_tier2_category(tier1: str, old_name: str, new_name: str):
    """
    Rename a tier2 category and cascade to all transactions and rules.

    Updates:
    - Category table entries where tier1=tier1 AND tier2=old_name
    - Transaction records where tier1=tier1 AND tier2=old_name
    - Rules where tier1=tier1 AND tier2=old_name
    """
    try:
        from backend.database.connection import get_db_context
        from backend.database.models import Category, Transaction, CategorizationRule

        with get_db_context() as db:
            # 1. Validate: Check for duplicates
            duplicate = db.query(Category).filter(
                Category.tier1 == tier1,
                Category.tier2 == new_name
            ).first()
            if duplicate:
                raise HTTPException(
                    status_code=400,
                    detail=f"Category '{tier1} > {new_name}' already exists"
                )

            # 2. Check if old_name exists
            existing = db.query(Category).filter(
                Category.tier1 == tier1,
                Category.tier2 == old_name
            ).first()
            if not existing:
                raise HTTPException(
                    status_code=404,
                    detail=f"Category '{tier1} > {old_name}' not found"
                )

            # 3. Update Category table
            db.query(Category).filter(
                Category.tier1 == tier1,
                Category.tier2 == old_name
            ).update(
                {Category.tier2: new_name},
                synchronize_session=False
            )

            # 4. CASCADE: Update transactions
            txn_count = db.query(Transaction).filter(
                Transaction.category_tier1 == tier1,
                Transaction.category_tier2 == old_name
            ).update(
                {Transaction.category_tier2: new_name},
                synchronize_session=False
            )

            # 5. CASCADE: Update rules
            rule_count = db.query(CategorizationRule).filter(
                CategorizationRule.category_tier1 == tier1,
                CategorizationRule.category_tier2 == old_name
            ).update(
                {CategorizationRule.category_tier2: new_name},
                synchronize_session=False
            )

            db.commit()

            logger.info(
                f"Renamed tier2 '{tier1} > {old_name}' -> '{new_name}': "
                f"{txn_count} transactions, {rule_count} rules updated"
            )

            return {
                'message': 'Tier2 category renamed successfully',
                'updated': {
                    'transactions': txn_count,
                    'rules': rule_count
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error renaming tier2 category: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tier3/{tier1}/{tier2}/{old_name}")
async def rename_tier3_category(tier1: str, tier2: str, old_name: str, new_name: str):
    """
    Rename a tier3 category and cascade to all transactions and rules.

    Updates:
    - Category table entries where tier1+tier2+tier3 match
    - Transaction records where all 3 tiers match
    - Rules where all 3 tiers match
    """
    try:
        from backend.database.connection import get_db_context
        from backend.database.models import Category, Transaction, CategorizationRule

        with get_db_context() as db:
            # 1. Validate: Check for duplicates
            duplicate = db.query(Category).filter(
                Category.tier1 == tier1,
                Category.tier2 == tier2,
                Category.tier3 == new_name
            ).first()
            if duplicate:
                raise HTTPException(
                    status_code=400,
                    detail=f"Category '{tier1} > {tier2} > {new_name}' already exists"
                )

            # 2. Check if old_name exists
            existing = db.query(Category).filter(
                Category.tier1 == tier1,
                Category.tier2 == tier2,
                Category.tier3 == old_name
            ).first()
            if not existing:
                raise HTTPException(
                    status_code=404,
                    detail=f"Category '{tier1} > {tier2} > {old_name}' not found"
                )

            # 3. Update Category table
            db.query(Category).filter(
                Category.tier1 == tier1,
                Category.tier2 == tier2,
                Category.tier3 == old_name
            ).update(
                {Category.tier3: new_name},
                synchronize_session=False
            )

            # 4. CASCADE: Update transactions
            txn_count = db.query(Transaction).filter(
                Transaction.category_tier1 == tier1,
                Transaction.category_tier2 == tier2,
                Transaction.category_tier3 == old_name
            ).update(
                {Transaction.category_tier3: new_name},
                synchronize_session=False
            )

            # 5. CASCADE: Update rules
            rule_count = db.query(CategorizationRule).filter(
                CategorizationRule.category_tier1 == tier1,
                CategorizationRule.category_tier2 == tier2,
                CategorizationRule.category_tier3 == old_name
            ).update(
                {CategorizationRule.category_tier3: new_name},
                synchronize_session=False
            )

            db.commit()

            logger.info(
                f"Renamed tier3 '{tier1} > {tier2} > {old_name}' -> '{new_name}': "
                f"{txn_count} transactions, {rule_count} rules updated"
            )

            return {
                'message': 'Tier3 category renamed successfully',
                'updated': {
                    'transactions': txn_count,
                    'rules': rule_count
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error renaming tier3 category: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
