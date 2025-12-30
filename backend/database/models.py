"""SQLAlchemy ORM Models"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Boolean, Column, DateTime, Integer, String, Numeric, Text, ForeignKey, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Institution(Base):
    """Financial institution (ČSOB, Partners Bank, Wise)"""
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)  # csob, partners, wise
    name = Column(String(100), nullable=False)  # "ČSOB", "Partners Bank"
    type = Column(String(20))  # bank, investment
    country = Column(String(2))  # CZ
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    accounts = relationship("Account", back_populates="institution")
    transactions = relationship("Transaction", back_populates="institution")


class Owner(Base):
    """Account owner for multi-person tracking"""
    __tablename__ = "owners"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)  # "Branislav", "Mirka"
    display_name = Column(String(100))  # "Branislav B."
    email = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    accounts = relationship("Account", back_populates="owner")
    transactions = relationship("Transaction", back_populates="owner")
    rules = relationship("CategorizationRule", back_populates="owner")


class Account(Base):
    """Bank account"""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_number = Column(String(50), unique=True, nullable=False)  # 283337817/0300
    account_name = Column(String(100))  # "Kreditka", "Brano Main"
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("owners.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    institution = relationship("Institution", back_populates="accounts")
    owner = relationship("Owner", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")


class Category(Base):
    """3-tier category hierarchy"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tier1 = Column(String(100), nullable=False)
    tier2 = Column(String(100), nullable=False)
    tier3 = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_categories_tier1", "tier1"),
        Index("idx_categories_tier2", "tier2"),
        Index("idx_categories_tiers", "tier1", "tier2", "tier3", unique=True),
    )


class Transaction(Base):
    """Financial transaction"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(50), unique=True, nullable=False)  # TXN_20241015_a3f5b8c9

    # Core fields
    date = Column(DateTime, nullable=False)
    description = Column(Text, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    amount_czk = Column(Numeric(15, 2))
    exchange_rate = Column(Numeric(10, 6))

    # 3-Tier categorization
    category_tier1 = Column(String(100))
    category_tier2 = Column(String(100))
    category_tier3 = Column(String(100))
    is_internal_transfer = Column(Boolean, default=False)

    # Categorization metadata
    categorization_source = Column(String(50))  # manual_rule, ai, internal_transfer, uncategorized
    ai_confidence = Column(Integer)  # 0-100

    # Classification
    account_id = Column(Integer, ForeignKey("accounts.id"))
    institution_id = Column(Integer, ForeignKey("institutions.id"))
    owner_id = Column(Integer, ForeignKey("owners.id"))
    transaction_type = Column(String(50))

    # Counterparty information
    counterparty_account = Column(String(50))
    counterparty_name = Column(String(255))
    counterparty_bank = Column(String(100))

    # Czech banking symbols
    variable_symbol = Column(String(20))
    constant_symbol = Column(String(20))
    specific_symbol = Column(String(20))
    reference = Column(String(100))
    note = Column(Text)

    # Metadata
    source_file = Column(String(255))
    processed_date = Column(DateTime, default=datetime.utcnow)
    synced_to_sheets = Column(Boolean, default=False)
    synced_at = Column(DateTime)

    # Relationships
    account = relationship("Account", back_populates="transactions")
    institution = relationship("Institution", back_populates="transactions")
    owner = relationship("Owner", back_populates="transactions")

    __table_args__ = (
        Index("idx_transactions_date", "date"),
        Index("idx_transactions_category", "category_tier1", "category_tier2", "category_tier3"),
        Index("idx_transactions_owner", "owner_id"),
        Index("idx_transactions_institution", "institution_id"),
        Index("idx_transactions_account", "account_id"),
        Index("idx_transactions_amount", "amount"),
        Index("idx_transactions_internal", "is_internal_transfer"),
        Index("idx_transactions_synced", "synced_to_sheets"),
    )


class CategorizationRule(Base):
    """Categorization rule for automatic transaction categorization"""
    __tablename__ = "categorization_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Rule identification
    name = Column(String(100))
    description = Column(Text)
    priority = Column(Integer, default=0)  # Higher = applied first
    is_active = Column(Boolean, default=True)

    # Matching conditions (stored as JSON)
    conditions = Column(Text, nullable=False)  # JSON string

    # Action: assign category
    category_tier1 = Column(String(100))
    category_tier2 = Column(String(100))
    category_tier3 = Column(String(100))

    # Optional: assign owner
    owner_id = Column(Integer, ForeignKey("owners.id"))

    # Optional: mark as internal transfer
    mark_as_internal = Column(Boolean, default=False)

    # Metadata
    created_by = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("Owner", back_populates="rules")

    __table_args__ = (
        Index("idx_rules_priority", "priority", postgresql_using="btree"),
        Index("idx_rules_active", "is_active"),
    )


class ImportJob(Base):
    """Track file import/processing status"""
    __tablename__ = "import_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"))
    status = Column(String(20), nullable=False)  # pending, processing, completed, failed

    # Statistics
    total_rows = Column(Integer)
    processed_rows = Column(Integer)
    failed_rows = Column(Integer)
    new_transactions = Column(Integer)
    duplicate_transactions = Column(Integer)

    # Error tracking
    error_message = Column(Text)
    error_details = Column(Text)  # JSON with row-level errors

    # Timestamps
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    institution = relationship("Institution")

    __table_args__ = (
        Index("idx_import_jobs_status", "status"),
        Index("idx_import_jobs_created", "created_at", postgresql_using="btree"),
    )


class SyncLog(Base):
    """Track Google Sheets sync operations"""
    __tablename__ = "sync_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sync_type = Column(String(20))  # sheets_to_db, db_to_sheets
    status = Column(String(20))  # success, partial, failed

    # Statistics
    records_synced = Column(Integer)
    records_failed = Column(Integer)

    # Details
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemSetting(Base):
    """Key-value store for system settings"""
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
