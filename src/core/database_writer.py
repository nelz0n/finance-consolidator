"""
Database writer for SQLite integration.

Writes normalized transactions to SQLite database for web service.
"""
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from src.models.transaction import Transaction
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseWriter:
    """Writes transactions to SQLite database"""

    def __init__(self, db_session=None):
        """
        Initialize database writer.

        Args:
            db_session: SQLAlchemy session (optional, will create if not provided)
        """
        self.db_session = db_session
        self._session_created = False

        if not self.db_session:
            from backend.database.connection import get_db_context
            self.db_context = get_db_context()
            self.db_session = self.db_context.__enter__()
            self._session_created = True

    def __del__(self):
        """Cleanup database session if we created it"""
        if self._session_created and hasattr(self, 'db_context'):
            try:
                self.db_context.__exit__(None, None, None)
            except:
                pass

    def write_transactions(
        self,
        transactions: List[Transaction],
        mode: str = "append"
    ) -> dict:
        """
        Write transactions to SQLite database.

        Args:
            transactions: List of Transaction objects to write
            mode: Write mode - "append" (skip duplicates) or "overwrite" (clear all)

        Returns:
            dict: Summary with counts of added/skipped/updated transactions
        """
        from backend.database.models import Transaction as DBTransaction
        from backend.database.models import Institution, Owner, Account
        from sqlalchemy.exc import IntegrityError

        if mode == "overwrite":
            logger.warning("OVERWRITE mode - clearing all transactions from database")
            self.db_session.query(DBTransaction).delete()
            self.db_session.commit()
            # Clear session cache to prevent stale duplicate checks
            self.db_session.expire_all()
            logger.info("Database cleared and session cache refreshed")

        added = 0
        skipped = 0
        updated = 0

        # Get or create institution/owner/account mappings
        institution_map = self._get_institution_map()
        owner_map = self._get_owner_map()

        for txn in transactions:
            try:
                # Check if transaction already exists
                existing = self.db_session.query(DBTransaction).filter(
                    DBTransaction.transaction_id == txn.transaction_id
                ).first()

                if existing and mode == "append":
                    skipped += 1
                    continue

                # Get foreign keys
                institution_id = institution_map.get(txn.institution)
                owner_id = owner_map.get(txn.owner)
                account_id = self._get_or_create_account(txn.account, institution_id, owner_id)

                # Convert Transaction model to database model
                db_txn = self._transaction_to_db(txn, institution_id, owner_id, account_id)

                if existing:
                    # Update existing transaction
                    for key, value in db_txn.items():
                        setattr(existing, key, value)
                    updated += 1
                else:
                    # Add new transaction
                    new_txn = DBTransaction(**db_txn)
                    self.db_session.add(new_txn)
                    added += 1

                # Commit in batches
                if (added + updated) % 100 == 0:
                    self.db_session.commit()
                    logger.info(f"Written {added + updated} transactions to database...")

            except IntegrityError as e:
                logger.warning(f"Duplicate transaction {txn.transaction_id}, skipping")
                self.db_session.rollback()
                skipped += 1
            except Exception as e:
                logger.error(f"Error writing transaction {txn.transaction_id}: {e}")
                self.db_session.rollback()
                continue

        # Final commit
        self.db_session.commit()

        summary = {
            "added": added,
            "skipped": skipped,
            "updated": updated,
            "total": len(transactions)
        }

        logger.info(f"Database write complete: {added} added, {updated} updated, {skipped} skipped")
        return summary

    def _get_institution_map(self) -> dict:
        """Get mapping of institution names to IDs"""
        from backend.database.models import Institution

        institutions = self.db_session.query(Institution).all()
        inst_map = {}

        # Map by name (case-insensitive)
        for inst in institutions:
            inst_map[inst.name.lower()] = inst.id

        # Add common variations
        if 'čsob' in inst_map:
            inst_map['csob'] = inst_map['čsob']
        if 'partners bank' in inst_map:
            inst_map['partners'] = inst_map['partners bank']

        return inst_map

    def _get_owner_map(self) -> dict:
        """Get mapping of owner names to IDs"""
        from backend.database.models import Owner

        owners = self.db_session.query(Owner).all()
        owner_map = {}

        for owner in owners:
            owner_map[owner.name.lower()] = owner.id

        return owner_map

    def _get_or_create_account(
        self,
        account_number: Optional[str],
        institution_id: Optional[int],
        owner_id: Optional[int]
    ) -> Optional[int]:
        """Get or create account record"""
        from backend.database.models import Account

        if not account_number:
            return None

        # Check if account exists
        account = self.db_session.query(Account).filter(
            Account.account_number == account_number
        ).first()

        if account:
            return account.id

        # Create new account
        new_account = Account(
            account_number=account_number,
            institution_id=institution_id,
            owner_id=owner_id,
            is_active=True
        )
        self.db_session.add(new_account)
        self.db_session.flush()

        logger.info(f"Created new account: {account_number}")
        return new_account.id

    def _transaction_to_db(
        self,
        txn: Transaction,
        institution_id: Optional[int],
        owner_id: Optional[int],
        account_id: Optional[int]
    ) -> dict:
        """Convert Transaction model to database dict"""

        # Convert Decimal to float for SQLite
        def to_float(val):
            if val is None:
                return None
            if isinstance(val, Decimal):
                return float(val)
            return val

        return {
            "transaction_id": txn.transaction_id,
            "date": txn.date,
            "description": txn.description or "",
            "amount": to_float(txn.amount),
            "currency": txn.currency,
            "amount_czk": to_float(txn.amount_czk),
            "exchange_rate": to_float(txn.exchange_rate),
            "category_tier1": txn.category_tier1,
            "category_tier2": txn.category_tier2,
            "category_tier3": txn.category_tier3,
            "is_internal_transfer": txn.is_internal_transfer or False,
            "categorization_source": txn.categorization_source,
            "ai_confidence": to_float(txn.ai_confidence),
            "account_id": account_id,
            "institution_id": institution_id,
            "owner_id": owner_id,
            "transaction_type": txn.transaction_type,
            "counterparty_account": txn.counterparty_account,
            "counterparty_name": txn.counterparty_name,
            "counterparty_bank": txn.counterparty_bank,
            "variable_symbol": txn.variable_symbol,
            "constant_symbol": txn.constant_symbol,
            "specific_symbol": txn.specific_symbol,
            "reference": txn.reference,
            "note": txn.note,
            "source_file": txn.source_file,
            "processed_date": datetime.now(),
            "synced_to_sheets": True,  # Mark as synced since we're writing from CLI
        }
