"""
Text Anonymization Utilities for VLA Inference API
Supports PII detection and removal including emails, phones, names, and addresses
"""

import re
from typing import List, Dict, Optional, Tuple
import logging

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logging.warning("spaCy not available. Named entity recognition will be disabled.")

logger = logging.getLogger(__name__)


class TextAnonymizer:
    """
    Comprehensive text anonymization for PII removal
    """

    # Regex patterns for PII detection
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

    # Phone patterns (US and international)
    PHONE_PATTERNS = [
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # US: 123-456-7890
        r'\b\(\d{3}\)\s*\d{3}[-.]?\d{4}\b',  # US: (123) 456-7890
        r'\b\+\d{1,3}\s?\d{1,4}\s?\d{1,4}\s?\d{1,9}\b',  # International
        r'\b\d{10}\b'  # 10 digits
    ]

    # SSN pattern
    SSN_PATTERN = r'\b\d{3}-\d{2}-\d{4}\b'

    # Credit card pattern (basic)
    CREDIT_CARD_PATTERN = r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'

    # Address patterns (simplified)
    ADDRESS_PATTERNS = [
        r'\b\d+\s+[A-Z][a-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct)\b',
        r'\b[A-Z][a-z]+,\s*[A-Z]{2}\s+\d{5}\b'  # City, ST ZIP
    ]

    # IP address pattern
    IP_PATTERN = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'

    def __init__(self, use_ner: bool = True):
        """
        Initialize text anonymizer with optional NER

        Args:
            use_ner: Enable named entity recognition for name detection
        """
        self.use_ner = use_ner and SPACY_AVAILABLE
        self.nlp = None

        if self.use_ner:
            try:
                # Try to load spaCy model
                self.nlp = spacy.load("en_core_web_sm")
            except Exception as e:
                logger.warning(f"Failed to load spaCy model: {e}")
                logger.warning("Name detection will use basic patterns only")
                self.nlp = None

    def anonymize_instruction(
        self,
        instruction: str,
        level: str = "full",
        preserve_context: bool = True
    ) -> str:
        """
        Anonymize text instruction by removing PII

        Args:
            instruction: Input text to anonymize
            level: Anonymization level - "basic", "full", or "maximum"
                - basic: Remove emails, phones, SSN, credit cards
                - full: Basic + names and addresses
                - maximum: Full + IP addresses and aggressive name matching
            preserve_context: Keep placeholder structure for context

        Returns:
            Anonymized text
        """
        if level not in ["basic", "full", "maximum"]:
            raise ValueError(f"Invalid anonymization level: {level}")

        anonymized = instruction
        replacements = []

        # Basic level: High-confidence PII
        if level in ["basic", "full", "maximum"]:
            anonymized, basic_repl = self._remove_basic_pii(anonymized, preserve_context)
            replacements.extend(basic_repl)

        # Full level: Add names and addresses
        if level in ["full", "maximum"]:
            anonymized, name_repl = self._remove_names(anonymized, preserve_context)
            replacements.extend(name_repl)
            anonymized, addr_repl = self._remove_addresses(anonymized, preserve_context)
            replacements.extend(addr_repl)

        # Maximum level: Aggressive matching
        if level == "maximum":
            anonymized, ip_repl = self._remove_ip_addresses(anonymized, preserve_context)
            replacements.extend(ip_repl)
            anonymized = self._aggressive_name_matching(anonymized, preserve_context)

        logger.info(f"Anonymized text with {len(replacements)} replacements at level '{level}'")
        return anonymized

    def _remove_basic_pii(
        self,
        text: str,
        preserve_context: bool
    ) -> Tuple[str, List[Dict]]:
        """Remove emails, phones, SSN, and credit cards"""
        replacements = []

        # Remove emails
        text, email_repl = self._remove_emails(text, preserve_context)
        replacements.extend(email_repl)

        # Remove phones
        text, phone_repl = self._remove_phones(text, preserve_context)
        replacements.extend(phone_repl)

        # Remove SSN
        text, ssn_repl = self._remove_ssn(text, preserve_context)
        replacements.extend(ssn_repl)

        # Remove credit cards
        text, cc_repl = self._remove_credit_cards(text, preserve_context)
        replacements.extend(cc_repl)

        return text, replacements

    def _remove_emails(self, text: str, preserve_context: bool) -> Tuple[str, List[Dict]]:
        """Remove email addresses"""
        replacements = []
        matches = list(re.finditer(self.EMAIL_PATTERN, text))

        for match in reversed(matches):  # Reverse to maintain indices
            original = match.group()
            replacement = "[EMAIL]" if preserve_context else ""
            text = text[:match.start()] + replacement + text[match.end():]
            replacements.append({"type": "email", "original": original})

        if matches:
            logger.debug(f"Removed {len(matches)} email address(es)")
        return text, replacements

    def _remove_phones(self, text: str, preserve_context: bool) -> Tuple[str, List[Dict]]:
        """Remove phone numbers"""
        replacements = []

        for pattern in self.PHONE_PATTERNS:
            matches = list(re.finditer(pattern, text))
            for match in reversed(matches):
                original = match.group()
                replacement = "[PHONE]" if preserve_context else ""
                text = text[:match.start()] + replacement + text[match.end():]
                replacements.append({"type": "phone", "original": original})

        if replacements:
            logger.debug(f"Removed {len(replacements)} phone number(s)")
        return text, replacements

    def _remove_ssn(self, text: str, preserve_context: bool) -> Tuple[str, List[Dict]]:
        """Remove Social Security Numbers"""
        replacements = []
        matches = list(re.finditer(self.SSN_PATTERN, text))

        for match in reversed(matches):
            original = match.group()
            replacement = "[SSN]" if preserve_context else ""
            text = text[:match.start()] + replacement + text[match.end():]
            replacements.append({"type": "ssn", "original": original})

        if matches:
            logger.debug(f"Removed {len(matches)} SSN(s)")
        return text, replacements

    def _remove_credit_cards(self, text: str, preserve_context: bool) -> Tuple[str, List[Dict]]:
        """Remove credit card numbers"""
        replacements = []
        matches = list(re.finditer(self.CREDIT_CARD_PATTERN, text))

        for match in reversed(matches):
            original = match.group()
            # Basic Luhn algorithm check to reduce false positives
            digits = re.sub(r'\D', '', original)
            if self._is_valid_card(digits):
                replacement = "[CREDIT_CARD]" if preserve_context else ""
                text = text[:match.start()] + replacement + text[match.end():]
                replacements.append({"type": "credit_card", "original": original})

        if replacements:
            logger.debug(f"Removed {len(replacements)} credit card(s)")
        return text, replacements

    def _is_valid_card(self, number: str) -> bool:
        """Simplified Luhn algorithm check"""
        if len(number) < 13 or len(number) > 19:
            return False

        def luhn_checksum(card_number):
            def digits_of(n):
                return [int(d) for d in str(n)]
            digits = digits_of(card_number)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d * 2))
            return checksum % 10

        return luhn_checksum(number) == 0

    def _remove_names(self, text: str, preserve_context: bool) -> Tuple[str, List[Dict]]:
        """Remove person names using NER or pattern matching"""
        replacements = []

        if self.nlp is not None:
            # Use spaCy NER for name detection
            doc = self.nlp(text)

            # Sort entities by start position (reverse for safe replacement)
            entities = sorted(
                [ent for ent in doc.ents if ent.label_ == "PERSON"],
                key=lambda x: x.start_char,
                reverse=True
            )

            for ent in entities:
                original = ent.text
                replacement = "[NAME]" if preserve_context else ""
                text = text[:ent.start_char] + replacement + text[ent.end_char:]
                replacements.append({"type": "name", "original": original})

            if entities:
                logger.debug(f"Removed {len(entities)} name(s) using NER")
        else:
            # Fallback to basic pattern matching
            # Look for capitalized words that might be names
            name_pattern = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
            matches = list(re.finditer(name_pattern, text))

            for match in reversed(matches):
                original = match.group()
                # Skip common words/phrases
                if original.lower() not in ["new york", "los angeles", "united states"]:
                    replacement = "[NAME]" if preserve_context else ""
                    text = text[:match.start()] + replacement + text[match.end():]
                    replacements.append({"type": "name", "original": original})

        return text, replacements

    def _remove_addresses(self, text: str, preserve_context: bool) -> Tuple[str, List[Dict]]:
        """Remove physical addresses"""
        replacements = []

        for pattern in self.ADDRESS_PATTERNS:
            matches = list(re.finditer(pattern, text))
            for match in reversed(matches):
                original = match.group()
                replacement = "[ADDRESS]" if preserve_context else ""
                text = text[:match.start()] + replacement + text[match.end():]
                replacements.append({"type": "address", "original": original})

        if replacements:
            logger.debug(f"Removed {len(replacements)} address(es)")
        return text, replacements

    def _remove_ip_addresses(self, text: str, preserve_context: bool) -> Tuple[str, List[Dict]]:
        """Remove IP addresses"""
        replacements = []
        matches = list(re.finditer(self.IP_PATTERN, text))

        for match in reversed(matches):
            original = match.group()
            # Validate IP format
            parts = original.split('.')
            if all(0 <= int(part) <= 255 for part in parts):
                replacement = "[IP_ADDRESS]" if preserve_context else ""
                text = text[:match.start()] + replacement + text[match.end():]
                replacements.append({"type": "ip_address", "original": original})

        if replacements:
            logger.debug(f"Removed {len(replacements)} IP address(es)")
        return text, replacements

    def _aggressive_name_matching(self, text: str, preserve_context: bool) -> str:
        """
        More aggressive name matching for maximum privacy
        Removes any capitalized word sequences that could be names
        """
        # Match 2-3 consecutive capitalized words
        pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b'
        replacement = "[NAME]" if preserve_context else ""
        text = re.sub(pattern, replacement, text)
        return text

    def detect_pii(self, text: str) -> Dict:
        """
        Detect PII without removing it

        Returns:
            Dictionary with PII detection results
        """
        results = {
            "emails": len(re.findall(self.EMAIL_PATTERN, text)),
            "phones": sum(len(re.findall(p, text)) for p in self.PHONE_PATTERNS),
            "ssn": len(re.findall(self.SSN_PATTERN, text)),
            "credit_cards": len(re.findall(self.CREDIT_CARD_PATTERN, text)),
            "addresses": sum(len(re.findall(p, text)) for p in self.ADDRESS_PATTERNS),
            "ip_addresses": len(re.findall(self.IP_PATTERN, text)),
            "names": 0,
            "total_pii_items": 0,
            "sensitivity_score": 0.0
        }

        # Count names if NER is available
        if self.nlp is not None:
            doc = self.nlp(text)
            results["names"] = len([ent for ent in doc.ents if ent.label_ == "PERSON"])

        # Calculate total and sensitivity score
        results["total_pii_items"] = sum(
            results[k] for k in results if k not in ["total_pii_items", "sensitivity_score"]
        )

        # Score based on PII types and counts (0-1)
        score = 0.0
        if results["emails"] > 0:
            score += 0.2
        if results["phones"] > 0:
            score += 0.2
        if results["ssn"] > 0:
            score += 0.3
        if results["credit_cards"] > 0:
            score += 0.3
        if results["names"] > 0:
            score += min(0.1 * results["names"], 0.3)
        if results["addresses"] > 0:
            score += 0.2

        results["sensitivity_score"] = min(score, 1.0)

        return results
