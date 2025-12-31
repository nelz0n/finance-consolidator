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

        # NOTE: Overwrite mode now updates existing transactions by transaction_id
        # instead of wiping the entire database. Append mode skips duplicates.
        if mode == "overwrite":
            logger.info("OVERWRITE mode - will update existing transactions and insert new ones")

        added = 0
        skipped = 0
        updated = 0

        # Get institution mappings
        institution_map = self._get_institution_map()

        logger.info(f"Institution map keys: {list(institution_map.keys())}")
        if transactions:
            logger.info(f"First transaction: institution={repr(transactions[0].institution)}, account={repr(transactions[0].account)}")

        logger.info(f"Starting transaction loop: {len(transactions)} transactions to process")
        for i, txn in enumerate(transactions):
            try:
                # Check if transaction already exists
                existing = self.db_session.query(DBTransaction).filter(
                    DBTransaction.transaction_id == txn.transaction_id
                ).first()

                # DEBUG: Log what we found
                if i < 3 or existing:  # Log first 3 and any duplicates
                    logger.info(f"Transaction {i+1}/{len(transactions)}: ID={txn.transaction_id}, existing={existing is not None}, mode={mode}")

                if existing and mode == "append":
                    logger.debug(f"Skipping duplicate in append mode: {txn.transaction_id}")
                    skipped += 1
                    continue

                # Get foreign keys (case-insensitive lookup for institution)
                institution_id = institution_map.get(txn.institution.lower() if txn.institution else None)

                # Get account description from central accounts.yaml
                account_description = self._get_account_description(txn.account)

                # Get or create account (no owner concept)
                account_id = self._get_or_create_account(txn.account, institution_id, account_description)

                # Convert Transaction model to database model (no owner_id)
                db_txn = self._transaction_to_db(txn, institution_id, account_id)

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

                # CRITICAL FIX: Commit after each transaction to avoid conflicts with flush() in _get_or_create_account()
                # The flush() can write pending transactions, causing IntegrityError on final commit
                self.db_session.commit()

                # Progress logging
                if (added + updated) % 10 == 0:
                    logger.info(f"Written {added + updated} transactions to database...")

            except IntegrityError as e:
                logger.error(f"IntegrityError for transaction {txn.transaction_id}: {str(e)}")
                logger.error(f"Error details: {e.orig if hasattr(e, 'orig') else 'no orig'}")
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

    def _get_account_description(self, account_number: Optional[str]) -> Optional[str]:
        """Get account description from central accounts.yaml config"""
        import yaml
        from pathlib import Path

        if not account_number:
            return None

        try:
            accounts_path = Path("config/accounts.yaml")
            if not accounts_path.exists():
                return None

            with open(accounts_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                accounts = config.get('accounts', {})
                account_info = accounts.get(account_number, {})
                return account_info.get('description')
        except Exception as e:
            logger.warning(f"Failed to load account description: {e}")
            return None

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

    def _get_or_create_account(
        self,
        account_number: Optional[str],
        institution_id: Optional[int],
        account_description: Optional[str]
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
            # Update description if changed
            if account_description and account.account_name != account_description:
                account.account_name = account_description
                logger.info(f"Updated account description: {account_number} -> {account_description}")
            return account.id

        # Create new account
        new_account = Account(
            account_number=account_number,
            account_name=account_description,
            institution_id=institution_id,
            owner_id=None,  # No owner concept
            is_active=True
        )
        self.db_session.add(new_account)
        self.db_session.flush()

        logger.info(f"Created new account: {account_number} ({account_description or 'no description'})")
        return new_account.id

    def _transaction_to_db(
        self,
        txn: Transaction,
        institution_id: Optional[int],
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
            "owner_id": None,  # No owner concept, managed via account
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
