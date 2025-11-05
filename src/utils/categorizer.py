"""
Transaction Categorization Engine

Handles 3-tier categorization with:
1. Internal transfer detection
2. Manual rules
3. Gemini AI fallback
4. Learning system
"""

import logging
import re
import os
import json
import yaml
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Any
from datetime import date, datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)


class TransactionCategorizer:
    """
    Comprehensive transaction categorization engine.

    Priority order:
    1. Internal transfer detection
    2. Manual rules (from config)
    3. Learned patterns
    4. Gemini AI fallback
    5. Uncategorized
    """

    def __init__(self, config_path: str = "config/categorization.yaml"):
        """
        Initialize categorizer.

        Args:
            config_path: Path to categorization config file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()

        # Internal transfer detection
        self.own_accounts = set(self.config.get('internal_transfers', {}).get('own_accounts', []))
        self.transfer_keywords = self.config.get('internal_transfers', {}).get(
            'detection_methods', []
        )

        # Manual rules
        self.manual_rules = self.config.get('manual_rules', [])
        # Sort by priority (higher first)
        self.manual_rules.sort(key=lambda r: r.get('priority', 0), reverse=True)

        # AI configuration
        self.ai_config = self.config.get('ai_fallback', {})
        self.ai_enabled = self.ai_config.get('enabled', False)

        # Learning system
        self.learning_enabled = self.config.get('learning', {}).get('enabled', False)
        self.learned_rules = self._load_learned_rules()

        # Category tree (for AI context)
        self.category_tree = self.config.get('category_tree', [])

        # Gemini API client (lazy init)
        self._gemini_client = None

        # Same-day transaction cache for detecting opposite amounts
        self._daily_transactions = {}

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

    def _load_learned_rules(self) -> List[Dict]:
        """Load learned rules from cache."""
        if not self.learning_enabled:
            return []

        learned_file = Path(self.config.get('learning', {}).get('learned_rules_file',
                                                                  'data/cache/learned_rules.yaml'))
        if not learned_file.exists():
            return []

        try:
            with open(learned_file, 'r', encoding='utf-8') as f:
                rules = yaml.safe_load(f) or []
            logger.info(f"Loaded {len(rules)} learned rules")
            return rules
        except Exception as e:
            logger.warning(f"Could not load learned rules: {e}")
            return []

    def categorize(self, transaction: Dict[str, Any]) -> Tuple[str, str, str, bool]:
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
            Tuple of (tier1, tier2, tier3, is_internal_transfer)
        """
        # 1. Check internal transfer
        if self._is_internal_transfer(transaction):
            logger.debug(f"Detected internal transfer: {transaction.get('description', '')[:50]}")
            transfer_cat = self.config.get('internal_transfers', {}).get('category', {})
            return (
                transfer_cat.get('tier1', 'Transfers'),
                transfer_cat.get('tier2', 'Internal Transfer'),
                transfer_cat.get('tier3', 'Between Own Accounts'),
                True  # is_internal_transfer
            )

        # 2. Try manual rules
        result = self._apply_manual_rules(transaction)
        if result:
            return result + (False,)  # Not internal transfer

        # 3. Try learned rules
        if self.learning_enabled:
            result = self._apply_learned_rules(transaction)
            if result:
                return result + (False,)

        # 4. Try AI fallback
        if self.ai_enabled:
            result = self._apply_ai_categorization(transaction)
            if result:
                return result + (False,)

        # 5. Default to uncategorized
        logger.debug(f"No category found for: {transaction.get('description', '')[:50]}")
        return ("Uncategorized", "Needs Review", "Unknown Transaction", False)

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

    def _apply_manual_rules(self, transaction: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
        """
        Apply manual categorization rules.

        Returns:
            (tier1, tier2, tier3) tuple if match found, None otherwise
        """
        for rule in self.manual_rules:
            if self._rule_matches(rule, transaction):
                category = rule.get('category', {})
                tier1 = category.get('tier1')
                tier2 = category.get('tier2')
                tier3 = category.get('tier3')

                logger.debug(f"Rule '{rule.get('name')}' matched: {tier1} > {tier2} > {tier3}")
                return (tier1, tier2, tier3)

        return None

    def _rule_matches(self, rule: Dict, transaction: Dict[str, Any]) -> bool:
        """
        Check if a rule matches a transaction.

        Rule format:
        match:
          type: "contains" | "exact" | "regex" | "amount_range" | "multi"
          field: "counterparty_name" | "description" | "amount" etc.
          value: "search string"
          pattern: "regex pattern" (for regex type)
        """
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

    def _apply_learned_rules(self, transaction: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
        """Apply learned rules (same format as manual rules)."""
        for rule in self.learned_rules:
            if self._rule_matches(rule, transaction):
                category = rule.get('category', {})
                return (category.get('tier1'), category.get('tier2'), category.get('tier3'))
        return None

    def _apply_ai_categorization(self, transaction: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
        """
        Use Gemini AI to categorize transaction.

        Returns:
            (tier1, tier2, tier3) tuple if successful, None otherwise
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

            return (tier1, tier2, tier3)

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

    def _call_gemini_api(self, prompt: str) -> str:
        """Call Gemini API with prompt."""
        import requests

        api_url = self.ai_config.get('api_url')
        api_key = self._gemini_api_key

        url = f"{api_url}?key={api_key}"

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }

        headers = {"Content-Type": "application/json"}

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()

        # Extract text from response
        text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')

        return text

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


def get_categorizer(config_path: str = "config/categorization.yaml") -> TransactionCategorizer:
    """Convenience function to get categorizer instance."""
    return TransactionCategorizer(config_path)
