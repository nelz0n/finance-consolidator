"""
Transaction Categorization Engine

Handles 3-tier categorization with:
1. Internal transfer detection
2. Manual rules (from Google Sheets or YAML)
3. Gemini AI fallback
"""

import logging
import re
import os
import json
import yaml
import time
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Any
from datetime import date, datetime, timedelta
from decimal import Decimal
from collections import deque

logger = logging.getLogger(__name__)


class TransactionCategorizer:
    """
    Comprehensive transaction categorization engine.

    Priority order:
    1. Internal transfer detection
    2. Manual rules (from Google Sheets or YAML)
    3. Gemini AI fallback
    4. Uncategorized
    """

    def __init__(self, config_path: str = "config/categorization.yaml",
                 settings_path: str = "config/settings.yaml",
                 reload_rules: bool = False):
        """
        Initialize categorizer.

        Args:
            config_path: Path to categorization config file
            settings_path: Path to settings file (for Google Sheets config)
            reload_rules: Force reload rules from Google Sheets (bypass cache)
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()

        # Load settings for Google Sheets configuration
        self.settings = self._load_settings(settings_path)
        self.reload_rules = reload_rules

        # Internal transfer detection
        self.own_accounts = set(self.config.get('internal_transfers', {}).get('own_accounts', []))
        self.transfer_keywords = self.config.get('internal_transfers', {}).get(
            'detection_methods', []
        )

        # Load manual rules (from Google Sheets or YAML)
        self.manual_rules = []
        self.owner_mapping = {}
        self._load_manual_rules()

        # AI configuration
        self.ai_config = self.config.get('ai_fallback', {})
        self.ai_enabled = self.ai_config.get('enabled', False)

        # Category tree (for AI context) - load from Sheets or YAML
        self.category_tree = []
        self._load_category_tree()

        # Gemini API client (lazy init)
        self._gemini_client = None

        # Same-day transaction cache for detecting opposite amounts
        self._daily_transactions = {}

        # Rate limiting for API calls
        self._api_call_timestamps = deque()  # Track timestamps of API calls
        self._daily_api_calls = 0
        self._daily_reset_time = None

        logger.info("Transaction categorizer initialized")

    def _load_config(self) -> Dict:
        """Load categorization configuration."""
        if not self.config_path.exists():
            logger.warning(f"Categorization config not found: {self.config_path}")
            return {}

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded categorization config from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading categorization config: {e}")
            return {}

    def _load_settings(self, settings_path: str) -> Dict:
        """Load settings configuration."""
        settings_file = Path(settings_path)
        if not settings_file.exists():
            logger.warning(f"Settings file not found: {settings_path}")
            return {}

        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = yaml.safe_load(f)
            return settings
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            return {}

    def _load_manual_rules(self):
        """Load manual rules from Google Sheets or YAML."""
        # Check if Google Sheets-based categorization is configured
        cat_config = self.settings.get('categorization', {})
        rules_source = cat_config.get('rules_source', 'yaml')

        if rules_source == 'google_sheets':
            logger.info("Loading categorization rules from Google Sheets...")
            self.manual_rules, self.owner_mapping = self._load_rules_from_sheets()
        else:
            logger.info("Loading categorization rules from YAML...")
            self.manual_rules = self.config.get('manual_rules', [])
            self.owner_mapping = {}

        # Sort by priority (higher first)
        if self.manual_rules:
            self.manual_rules.sort(key=lambda r: r.get('priority', 0), reverse=True)
            logger.info(f"Loaded {len(self.manual_rules)} manual rules")

    def _load_rules_from_sheets(self) -> Tuple[List[Dict], Dict[str, str]]:
        """
        Load categorization rules from Google Sheets.

        Returns:
            Tuple of (rules list, owner mapping dict)
        """
        cat_config = self.settings.get('categorization', {})
        cache_enabled = cat_config.get('cache_enabled', True)
        cache_file = Path(cat_config.get('cache_file', 'data/cache/sheets_rules.yaml'))
        cache_ttl_hours = cat_config.get('cache_ttl_hours', 24)

        # Check cache first (if not force reload)
        if cache_enabled and not self.reload_rules:
            cached_data = self._check_cache(cache_file, cache_ttl_hours)
            if cached_data:
                logger.info(f"Using cached rules from {cache_file}")
                return (
                    cached_data.get('rules', []),
                    cached_data.get('owner_mapping', {})
                )

        # Load from Google Sheets
        try:
            from src.connectors.google_sheets import GoogleSheetsConnector

            sheets_config = cat_config.get('google_sheets', {})
            spreadsheet_id = sheets_config.get('spreadsheet_id',
                                              self.settings.get('google_sheets', {}).get('master_sheet_id'))
            rules_tab = sheets_config.get('rules_tab', 'Categorization_Rules')
            owner_tab = sheets_config.get('owner_mapping_tab', 'Owner_Mapping')

            # Get credentials paths
            creds_path = self.settings.get('google_drive', {}).get('credentials_path')
            token_path = self.settings.get('google_drive', {}).get('token_path')

            # Connect to Google Sheets
            connector = GoogleSheetsConnector(creds_path, token_path)
            if not connector.authenticate():
                logger.error("Failed to authenticate with Google Sheets")
                return ([], {})

            # Load rules
            rules_data = connector.read_sheet(spreadsheet_id, f"{rules_tab}!A:L")
            if not rules_data or len(rules_data) < 2:
                logger.warning(f"No rules found in {rules_tab}")
                return ([], {})

            # Parse rules (skip header row)
            headers = rules_data[0]
            rules = []
            for row in rules_data[1:]:
                if len(row) < 12:
                    # Pad row with empty strings
                    row = row + [''] * (12 - len(row))

                rule = {
                    'priority': int(row[0]) if row[0] else 0,
                    'description_contains': row[1].strip() if row[1] else '',
                    'institution_exact': row[2].strip() if row[2] else '',
                    'counterparty_account_exact': row[3].strip() if row[3] else '',
                    'counterparty_name_contains': row[4].strip() if row[4] else '',
                    'variable_symbol_exact': row[5].strip() if row[5] else '',
                    'amount_czk_min': float(row[6]) if row[6] else None,
                    'amount_czk_max': float(row[7]) if row[7] else None,
                    'tier1': row[8].strip() if row[8] else '',
                    'tier2': row[9].strip() if row[9] else '',
                    'tier3': row[10].strip() if row[10] else '',
                    'owner': row[11].strip() if row[11] else '',
                }
                rules.append(rule)

            logger.info(f"Loaded {len(rules)} rules from Google Sheets")

            # Load owner mapping
            owner_data = connector.read_sheet(spreadsheet_id, f"{owner_tab}!A:B")
            owner_mapping = {}
            if owner_data and len(owner_data) > 1:
                for row in owner_data[1:]:  # Skip header
                    if len(row) >= 2:
                        account = row[0].strip()
                        owner = row[1].strip()
                        if account and owner:
                            owner_mapping[account] = owner

                logger.info(f"Loaded {len(owner_mapping)} owner mappings from Google Sheets")

            # Cache the results
            if cache_enabled:
                self._save_cache(cache_file, rules, owner_mapping)

            return (rules, owner_mapping)

        except Exception as e:
            logger.error(f"Error loading rules from Google Sheets: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return ([], {})

    def _check_cache(self, cache_file: Path, ttl_hours: int) -> Optional[Dict]:
        """
        Check if cached rules are still valid.

        Args:
            cache_file: Path to cache file
            ttl_hours: Time-to-live in hours

        Returns:
            Cached data if valid, None otherwise
        """
        if not cache_file.exists():
            return None

        try:
            # Check file age
            file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if file_age.total_seconds() > ttl_hours * 3600:
                logger.info(f"Cache expired (age: {file_age.total_seconds() / 3600:.1f}h > {ttl_hours}h)")
                return None

            # Load cache
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = yaml.safe_load(f)

            logger.info(f"Cache valid (age: {file_age.total_seconds() / 3600:.1f}h)")
            return cached_data

        except Exception as e:
            logger.warning(f"Error reading cache: {e}")
            return None

    def _save_cache(self, cache_file: Path, rules: List[Dict], owner_mapping: Dict[str, str]):
        """Save rules to cache file."""
        try:
            # Ensure directory exists
            cache_file.parent.mkdir(parents=True, exist_ok=True)

            # Save to file
            cache_data = {
                'rules': rules,
                'owner_mapping': owner_mapping,
                'cached_at': datetime.now().isoformat()
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                yaml.dump(cache_data, f, default_flow_style=False, allow_unicode=True)

            logger.info(f"Saved {len(rules)} rules to cache: {cache_file}")

        except Exception as e:
            logger.warning(f"Error saving cache: {e}")

    def _load_category_tree(self):
        """Load category tree from Google Sheets or YAML."""
        cat_config = self.settings.get('categorization', {})
        rules_source = cat_config.get('rules_source', 'yaml')

        if rules_source == 'google_sheets':
            logger.info("Loading category tree from Google Sheets...")
            self.category_tree = self._load_category_tree_from_sheets()
        else:
            logger.info("Loading category tree from YAML...")
            self.category_tree = self.config.get('category_tree', [])

        if self.category_tree:
            logger.info(f"Loaded category tree with {len(self.category_tree)} tier1 categories")

    def _load_category_tree_from_sheets(self) -> List[Dict]:
        """
        Load category tree from Google Sheets Categories tab.

        Returns:
            List of tier1 categories with nested tier2 and tier3
        """
        try:
            from src.connectors.google_sheets import GoogleSheetsConnector

            cat_config = self.settings.get('categorization', {})
            sheets_config = cat_config.get('google_sheets', {})
            spreadsheet_id = sheets_config.get('spreadsheet_id',
                                              self.settings.get('google_sheets', {}).get('master_sheet_id'))
            categories_tab = sheets_config.get('categories_tab', 'Categories')

            # Get credentials paths
            creds_path = self.settings.get('google_drive', {}).get('credentials_path')
            token_path = self.settings.get('google_drive', {}).get('token_path')

            # Connect to Google Sheets
            connector = GoogleSheetsConnector(creds_path, token_path)
            if not connector.authenticate():
                logger.error("Failed to authenticate with Google Sheets")
                return []

            # Load categories (columns A-C: Tier1, Tier2, Tier3)
            categories_data = connector.read_sheet(spreadsheet_id, f"{categories_tab}!A:C")
            if not categories_data or len(categories_data) < 2:
                logger.warning(f"No categories found in {categories_tab}")
                return []

            # Parse into hierarchical structure
            category_tree = {}  # tier1 -> tier2 -> [tier3]

            # Skip header row
            for row in categories_data[1:]:
                if len(row) < 3:
                    continue

                tier1 = row[0].strip() if row[0] else ""
                tier2 = row[1].strip() if row[1] else ""
                tier3 = row[2].strip() if row[2] else ""

                if not tier1 or not tier2 or not tier3:
                    continue

                # Build hierarchy
                if tier1 not in category_tree:
                    category_tree[tier1] = {}

                if tier2 not in category_tree[tier1]:
                    category_tree[tier1][tier2] = []

                if tier3 not in category_tree[tier1][tier2]:
                    category_tree[tier1][tier2].append(tier3)

            # Convert to expected format
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

            logger.info(f"Loaded category tree from Google Sheets: {len(result)} tier1 categories")
            return result

        except Exception as e:
            logger.error(f"Error loading category tree from Google Sheets: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []


    def categorize(self, transaction: Dict[str, Any]) -> Tuple[str, str, str, str, bool, str, Optional[int]]:
        """
        Categorize a transaction.

        Args:
            transaction: Transaction dictionary with fields:
                - description
                - counterparty_name
                - counterparty_account
                - amount
                - date
                - account
                etc.

        Returns:
            Tuple of (tier1, tier2, tier3, owner, is_internal_transfer, categorization_source, ai_confidence)
            - categorization_source: "internal_transfer", "manual_rule", "ai", or "uncategorized"
            - ai_confidence: 0-100 if source is "ai", None otherwise
        """
        # 1. Check internal transfer
        if self._is_internal_transfer(transaction):
            logger.debug(f"Detected internal transfer: {transaction.get('description', '')[:50]}")
            transfer_cat = self.config.get('internal_transfers', {}).get('category', {})
            # Owner still determined by fallback for internal transfers
            owner = self._determine_owner(transaction)
            return (
                transfer_cat.get('tier1', 'Transfers'),
                transfer_cat.get('tier2', 'Internal Transfer'),
                transfer_cat.get('tier3', 'Between Own Accounts'),
                owner,
                True,  # is_internal_transfer
                'internal_transfer',  # categorization_source
                None  # ai_confidence
            )

        # 2. Try manual rules (now returns owner too)
        result = self._apply_manual_rules(transaction)
        if result:
            tier1, tier2, tier3, owner_from_rule = result
            # If owner not in rule, use fallback
            if not owner_from_rule:
                owner_from_rule = self._determine_owner(transaction)
            return (tier1, tier2, tier3, owner_from_rule, False, 'manual_rule', None)

        # 3. Try AI fallback
        if self.ai_enabled:
            result = self._apply_ai_categorization(transaction)
            if result:
                tier1, tier2, tier3, confidence = result
                owner = self._determine_owner(transaction)
                return (tier1, tier2, tier3, owner, False, 'ai', confidence)

        # 4. Default to uncategorized
        logger.debug(f"No category found for: {transaction.get('description', '')[:50]}")
        owner = self._determine_owner(transaction)
        return ("Uncategorized", "Needs Review", "Unknown Transaction", owner, False, 'uncategorized', None)

    def _determine_owner(self, transaction: Dict[str, Any]) -> str:
        """
        Determine owner from owner_mapping or fallback to transaction's existing owner.

        Args:
            transaction: Transaction dictionary

        Returns:
            Owner name
        """
        account = transaction.get('account', '')

        # Check owner_mapping (from Google Sheets or config)
        if account in self.owner_mapping:
            return self.owner_mapping[account]

        # Try without bank code (e.g., "283337817/0300" -> "283337817")
        if '/' in account:
            account_base = account.split('/')[0]
            if account_base in self.owner_mapping:
                return self.owner_mapping[account_base]

        # Fallback to transaction's existing owner field
        return transaction.get('owner', 'Unknown')

    def _is_internal_transfer(self, transaction: Dict[str, Any]) -> bool:
        """
        Detect if transaction is an internal transfer.

        Methods:
        1. Counterparty account in own accounts
        2. Description keywords
        3. Same-day opposite amount (optional)
        """
        # Check exclusions first - if any exclusion matches, NOT an internal transfer
        exclusions = self.config.get('internal_transfers', {}).get('exclusions', {})

        # Exclude specific counterparty names (e.g., TransferWise cashback, Amazon refunds)
        exclude_counterparty_names = exclusions.get('counterparty_names', [])
        counterparty_name = transaction.get('counterparty_name', '')
        if counterparty_name in exclude_counterparty_names:
            logger.debug(f"Excluded from internal transfer: counterparty_name '{counterparty_name}' in exclusion list")
            return False

        # Exclude specific transaction types (e.g., Úroky/Interest is income, not transfer)
        exclude_transaction_types = exclusions.get('transaction_types', [])
        transaction_type = transaction.get('type', '')
        if transaction_type in exclude_transaction_types:
            logger.debug(f"Excluded from internal transfer: transaction_type '{transaction_type}' in exclusion list")
            return False

        # Now proceed with detection methods
        detection_methods = self.config.get('internal_transfers', {}).get('detection_methods', [])

        # Debug: Log what we're checking
        account = transaction.get('account', '')
        counterparty = transaction.get('counterparty_account', '')
        logger.debug(f"Checking internal transfer: account='{account}', counterparty='{counterparty}', own_accounts={self.own_accounts}")

        for method in detection_methods:
            if not method.get('enabled', True):
                continue

            method_type = method.get('type')

            # Method 1: Counterparty in own accounts
            if method_type == 'counterparty_in_own_accounts':
                # Try exact match first
                if counterparty in self.own_accounts:
                    logger.info(f"✓ Internal transfer detected: counterparty '{counterparty}' in own accounts (exact match)")
                    return True

                # Fallback: Try matching base account number (without bank code)
                # This handles format variations like "123456789" vs "123456789/0300"
                if counterparty:
                    counterparty_base = counterparty.split('/')[0] if '/' in counterparty else counterparty
                    for own_account in self.own_accounts:
                        own_account_base = own_account.split('/')[0] if '/' in own_account else own_account
                        if counterparty_base == own_account_base:
                            logger.info(f"✓ Internal transfer detected: counterparty base '{counterparty_base}' matches own account '{own_account}' (flexible match)")
                            return True

                # Also check if it's a self-transfer (account == counterparty_account)
                # This catches transfers between own accounts (e.g., credit card payment)
                if account and counterparty:
                    # Try exact match first
                    if account == counterparty:
                        logger.info(f"✓ Internal transfer detected: self-transfer '{account}' == '{counterparty}'")
                        return True

                    # Try base account numbers (without bank codes)
                    account_base = account.split('/')[0] if '/' in account else account
                    counterparty_base = counterparty.split('/')[0] if '/' in counterparty else counterparty
                    if account_base == counterparty_base:
                        logger.info(f"✓ Internal transfer detected: self-transfer base '{account_base}' == '{counterparty_base}'")
                        return True

                logger.debug(f"✗ No match: counterparty='{counterparty}' not in own_accounts and not self-transfer")

            # Method 2: Description keywords
            elif method_type == 'description_keywords':
                description = transaction.get('description', '').upper()
                counterparty_name = transaction.get('counterparty_name', '').upper()
                keywords = method.get('keywords', [])

                for keyword in keywords:
                    if keyword.upper() in description or keyword.upper() in counterparty_name:
                        logger.debug(f"Internal transfer detected: keyword '{keyword}' found")
                        return True

            # Method 3: Same-day opposite amount (advanced)
            elif method_type == 'same_day_opposite_amount':
                # This requires looking at other transactions - implement later
                pass

        return False

    def _apply_manual_rules(self, transaction: Dict[str, Any]) -> Optional[Tuple[str, str, str, str]]:
        """
        Apply manual categorization rules.

        Returns:
            (tier1, tier2, tier3, owner) tuple if match found, None otherwise
        """
        for rule in self.manual_rules:
            if self._rule_matches(rule, transaction):
                # Check if this is new Google Sheets format (tier1, tier2, tier3 at top level)
                if 'tier1' in rule:
                    tier1 = rule.get('tier1', '')
                    tier2 = rule.get('tier2', '')
                    tier3 = rule.get('tier3', '')
                    owner = rule.get('owner', '')
                else:
                    # Old YAML format (category dict)
                    category = rule.get('category', {})
                    tier1 = category.get('tier1')
                    tier2 = category.get('tier2')
                    tier3 = category.get('tier3')
                    owner = ''

                logger.debug(f"Rule matched: {tier1} > {tier2} > {tier3}" + (f" (owner: {owner})" if owner else ""))
                return (tier1, tier2, tier3, owner)

        return None

    def _sheets_rule_matches(self, rule: Dict, transaction: Dict[str, Any]) -> bool:
        """
        Match rule in Google Sheets format (simple AND logic).

        All non-empty conditions must match.

        Fields:
        - description_contains: Check if description contains string (case-insensitive)
        - institution_exact: Check if institution matches exactly (case-insensitive)
        - counterparty_account_exact: Check if counterparty_account matches exactly
        - counterparty_name_contains: Check if counterparty_name contains string (case-insensitive)
        - variable_symbol_exact: Check if variable_symbol matches exactly
        - amount_czk_min: Minimum amount in CZK
        - amount_czk_max: Maximum amount in CZK
        """
        # Get transaction fields
        description = str(transaction.get('description', '')).upper()
        institution = str(transaction.get('institution', '')).upper()
        counterparty_account = str(transaction.get('counterparty_account', '')).strip()
        counterparty_name = str(transaction.get('counterparty_name', '')).upper()
        variable_symbol = str(transaction.get('variable_symbol', '')).strip()
        amount_czk = transaction.get('amount_czk', 0)
        if isinstance(amount_czk, Decimal):
            amount_czk = float(amount_czk)

        # Check description contains
        desc_check = rule.get('description_contains', '').strip()
        if desc_check:
            if desc_check.upper() not in description:
                return False

        # Check institution exact
        inst_check = rule.get('institution_exact', '').strip()
        if inst_check:
            if inst_check.upper() != institution:
                return False

        # Check counterparty account exact
        cp_account_check = rule.get('counterparty_account_exact', '').strip()
        if cp_account_check:
            if cp_account_check != counterparty_account:
                return False

        # Check counterparty name contains
        cp_name_check = rule.get('counterparty_name_contains', '').strip()
        if cp_name_check:
            if cp_name_check.upper() not in counterparty_name:
                return False

        # Check variable symbol exact
        vs_check = rule.get('variable_symbol_exact', '').strip()
        if vs_check:
            if vs_check != variable_symbol:
                return False

        # Check amount range
        amount_min = rule.get('amount_czk_min')
        amount_max = rule.get('amount_czk_max')

        if amount_min is not None:
            if amount_czk < amount_min:
                return False

        if amount_max is not None:
            if amount_czk > amount_max:
                return False

        # All conditions matched
        return True

    def _rule_matches(self, rule: Dict, transaction: Dict[str, Any]) -> bool:
        """
        Check if a rule matches a transaction.

        Supports two formats:
        1. New Google Sheets format (simple AND logic with specific fields)
        2. Old YAML format (match dict with type, field, value)
        """
        # Check if this is new Google Sheets format
        if 'description_contains' in rule or 'institution_exact' in rule:
            return self._sheets_rule_matches(rule, transaction)

        # Old YAML format
        match = rule.get('match', {})
        match_type = match.get('type')

        if match_type == 'contains':
            field = match.get('field')
            value = match.get('value', '').upper()
            field_value = str(transaction.get(field, '')).upper()
            return value in field_value

        elif match_type == 'exact':
            field = match.get('field')
            value = match.get('value')
            field_value = transaction.get(field)
            return str(field_value).upper() == str(value).upper()

        elif match_type == 'regex':
            field = match.get('field')
            pattern = match.get('pattern')
            field_value = str(transaction.get(field, ''))
            try:
                return bool(re.search(pattern, field_value, re.IGNORECASE))
            except re.error:
                logger.warning(f"Invalid regex pattern: {pattern}")
                return False

        elif match_type == 'amount_range':
            amount = transaction.get('amount', 0)
            if isinstance(amount, Decimal):
                amount = float(amount)

            min_amount = match.get('min_amount', float('-inf'))
            max_amount = match.get('max_amount', float('inf'))

            # Also check optional description contains
            desc_check = True
            if 'description_contains' in match:
                desc_value = match.get('description_contains', '').upper()
                description = str(transaction.get('description', '')).upper()
                desc_check = desc_value in description

            return min_amount <= amount <= max_amount and desc_check

        elif match_type == 'multi':
            # Multiple conditions (AND)
            conditions = match.get('conditions', [])
            for condition in conditions:
                field = condition.get('field')
                field_value = transaction.get(field)

                if 'contains' in condition:
                    if condition['contains'].upper() not in str(field_value).upper():
                        return False
                elif 'equals' in condition:
                    if str(field_value).upper() != str(condition['equals']).upper():
                        return False
                elif 'greater_than' in condition:
                    if not (field_value and float(field_value) > condition['greater_than']):
                        return False
                elif 'less_than' in condition:
                    if not (field_value and float(field_value) < condition['less_than']):
                        return False

            return True  # All conditions passed

        return False

    def _apply_ai_categorization(self, transaction: Dict[str, Any]) -> Optional[Tuple[str, str, str, int]]:
        """
        Use Gemini AI to categorize transaction.

        Returns:
            (tier1, tier2, tier3, confidence) tuple if successful, None otherwise
        """
        try:
            if not self._gemini_client:
                self._init_gemini_client()

            if not self._gemini_client:
                return None

            # Build prompt
            prompt = self._build_ai_prompt(transaction)

            # Call Gemini API
            response = self._call_gemini_api(prompt)

            # Parse response
            tier1, tier2, tier3, confidence = self._parse_ai_response(response)

            # Check confidence threshold
            threshold = self.ai_config.get('confidence_threshold', 75)
            if confidence < threshold:
                logger.debug(f"AI confidence {confidence}% below threshold {threshold}%")
                return None

            logger.info(f"AI categorized: {tier1} > {tier2} > {tier3} ({confidence}% confidence)")

            # Cache result if enabled
            if self.ai_config.get('cache_results', False):
                self._cache_ai_result(transaction, (tier1, tier2, tier3))

            return (tier1, tier2, tier3, confidence)

        except Exception as e:
            logger.error(f"AI categorization failed: {e}")
            return None

    def _init_gemini_client(self):
        """Initialize Gemini API client."""
        api_key_env = self.ai_config.get('api_key_env', 'GEMINI_API_KEY')
        api_key = os.getenv(api_key_env)

        if not api_key:
            logger.warning(f"Gemini API key not found in environment variable '{api_key_env}'")
            logger.info("Set GEMINI_API_KEY environment variable to enable AI categorization")
            self.ai_enabled = False
            return

        # Store API key for requests
        self._gemini_api_key = api_key
        self._gemini_client = True  # Flag that it's initialized

    def _build_ai_prompt(self, transaction: Dict[str, Any]) -> str:
        """Build prompt for Gemini API."""
        # Get category tree summary
        category_summary = self._get_category_tree_summary()

        # Build prompt from template
        template = self.ai_config.get('prompt_template', '')

        prompt = template.format(
            date=transaction.get('date', ''),
            amount=transaction.get('amount', ''),
            currency=transaction.get('currency', 'CZK'),
            description=transaction.get('description', ''),
            counterparty_name=transaction.get('counterparty_name', ''),
            counterparty_account=transaction.get('counterparty_account', ''),
            category_tree_summary=category_summary
        )

        return prompt

    def _get_category_tree_summary(self) -> str:
        """Get formatted category tree for AI prompt."""
        lines = []
        for tier1_cat in self.category_tree:
            tier1 = tier1_cat.get('tier1')
            lines.append(f"\n{tier1}:")

            for tier2_cat in tier1_cat.get('tier2_categories', []):
                tier2 = tier2_cat.get('tier2')
                tier3_list = tier2_cat.get('tier3', [])
                tier3_sample = ', '.join(tier3_list[:3])  # Show first 3
                if len(tier3_list) > 3:
                    tier3_sample += '...'
                lines.append(f"  - {tier2}: {tier3_sample}")

        return '\n'.join(lines)

    def _wait_for_rate_limit(self):
        """
        Enforce rate limiting before making API call.

        Uses token bucket algorithm with both per-minute and per-day limits.
        """
        rate_limit_config = self.ai_config.get('rate_limit', {})
        requests_per_minute = rate_limit_config.get('requests_per_minute', 10)
        requests_per_day = rate_limit_config.get('requests_per_day', 1000)

        current_time = time.time()

        # Check daily limit
        if self._daily_reset_time is None or current_time >= self._daily_reset_time:
            # Reset daily counter (resets at midnight or after 24h)
            self._daily_api_calls = 0
            self._daily_reset_time = current_time + 86400  # 24 hours

        if self._daily_api_calls >= requests_per_day:
            logger.error(f"Daily API limit reached ({requests_per_day} calls/day)")
            raise Exception(f"Daily API limit of {requests_per_day} calls reached")

        # Remove timestamps older than 1 minute
        minute_ago = current_time - 60
        while self._api_call_timestamps and self._api_call_timestamps[0] < minute_ago:
            self._api_call_timestamps.popleft()

        # Check per-minute limit
        if len(self._api_call_timestamps) >= requests_per_minute:
            # Calculate wait time until oldest call falls out of window
            wait_time = 60 - (current_time - self._api_call_timestamps[0])
            if wait_time > 0:
                logger.info(f"Rate limit: waiting {wait_time:.1f}s before next API call")
                time.sleep(wait_time)
                # Clean up old timestamps after waiting
                current_time = time.time()
                minute_ago = current_time - 60
                while self._api_call_timestamps and self._api_call_timestamps[0] < minute_ago:
                    self._api_call_timestamps.popleft()

        # Record this call
        self._api_call_timestamps.append(current_time)
        self._daily_api_calls += 1

    def _call_gemini_api(self, prompt: str) -> str:
        """
        Call Gemini API with prompt, including rate limiting and retry logic.

        Implements:
        - Rate limiting (requests per minute/day)
        - Exponential backoff for 429 errors
        - Configurable retry attempts
        """
        import requests

        api_base_url = self.ai_config.get('api_url')
        model = self.ai_config.get('model', 'gemini-1.5-flash')
        api_key = self._gemini_api_key

        # Retry configuration
        max_retries = self.ai_config.get('max_retries', 3)
        base_delay = self.ai_config.get('retry_base_delay', 2)  # seconds

        # Construct full URL: base_url/models/model_name:generateContent
        url = f"{api_base_url}/models/{model}:generateContent"

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }

        # Use x-goog-api-key header (official API format)
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        }

        # Retry loop with exponential backoff
        for attempt in range(max_retries):
            try:
                # Wait for rate limit before making call
                self._wait_for_rate_limit()

                # Make API request
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()

                data = response.json()

                # Extract text from response
                text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')

                return text

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    # Rate limit error - apply exponential backoff
                    if attempt < max_retries - 1:
                        wait_time = base_delay * (2 ** attempt)
                        logger.warning(f"429 Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"429 Rate limit error after {max_retries} attempts")
                        raise
                else:
                    # Other HTTP error - don't retry
                    logger.error(f"HTTP error {e.response.status_code}: {e}")
                    raise

            except Exception as e:
                logger.error(f"API call failed on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    wait_time = base_delay * (2 ** attempt)
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

        raise Exception("API call failed after all retries")

    def _parse_ai_response(self, response: str) -> Tuple[str, str, str, int]:
        """
        Parse AI response.

        Expected format:
        Tier1: [value]
        Tier2: [value]
        Tier3: [value]
        Confidence: [0-100]
        """
        tier1 = tier2 = tier3 = None
        confidence = 0

        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('Tier1:'):
                tier1 = line.split(':', 1)[1].strip()
            elif line.startswith('Tier2:'):
                tier2 = line.split(':', 1)[1].strip()
            elif line.startswith('Tier3:'):
                tier3 = line.split(':', 1)[1].strip()
            elif line.startswith('Confidence:'):
                try:
                    confidence = int(line.split(':', 1)[1].strip().replace('%', ''))
                except ValueError:
                    confidence = 0

        if not all([tier1, tier2, tier3]):
            raise ValueError(f"Could not parse AI response: {response}")

        return tier1, tier2, tier3, confidence

    def _cache_ai_result(self, transaction: Dict[str, Any], category: Tuple[str, str, str]):
        """Cache AI categorization result."""
        cache_file = Path(self.ai_config.get('cache_file', 'data/cache/ai_category_cache.json'))
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing cache
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        else:
            cache = []

        # Create cache entry
        entry = {
            'description': transaction.get('description'),
            'counterparty_name': transaction.get('counterparty_name'),
            'amount': float(transaction.get('amount', 0)) if transaction.get('amount') else None,
            'category': {
                'tier1': category[0],
                'tier2': category[1],
                'tier3': category[2]
            },
            'timestamp': datetime.now().isoformat()
        }

        cache.append(entry)

        # Save cache
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)


def get_categorizer(config_path: str = "config/categorization.yaml",
                   settings_path: str = "config/settings.yaml",
                   reload_rules: bool = False) -> TransactionCategorizer:
    """
    Convenience function to get categorizer instance.

    Args:
        config_path: Path to categorization config file
        settings_path: Path to settings file
        reload_rules: Force reload rules from Google Sheets (bypass cache)

    Returns:
        TransactionCategorizer instance
    """
    return TransactionCategorizer(config_path, settings_path, reload_rules)
