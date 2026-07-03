"""
Phase 2 — PII Redaction
Uses Microsoft Presidio with custom Pakistani recognizers.
Redacts: CNIC, card numbers, Pakistani phone numbers, emails, person names.
"""

from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig


# ── Custom Pakistani recognizers ──────────────────────────────────────────────

def build_cnic_recognizer() -> PatternRecognizer:
    """Pakistani CNIC: XXXXX-XXXXXXX-X or 13 digits."""
    return PatternRecognizer(
        supported_entity="PK_CNIC",
        patterns=[
            Pattern("CNIC with dashes", r"\b\d{5}-\d{7}-\d\b", 0.95),
            Pattern("CNIC no dashes",   r"\b\d{13}\b",          0.6),
        ]
    )


def build_pk_phone_recognizer() -> PatternRecognizer:
    """Pakistani phone numbers: 03XX-XXXXXXX, +923XXXXXXXXX, 923XXXXXXXXX."""
    return PatternRecognizer(
        supported_entity="PK_PHONE",
        patterns=[
            Pattern("PK phone dashes",   r"\b03\d{2}-\d{7}\b",       0.95),
            Pattern("PK phone plain",    r"\b03\d{9}\b",              0.90),
            Pattern("PK phone intl +",   r"\+923\d{9}\b",             0.95),
            Pattern("PK phone intl 92",  r"\b923\d{9}\b",             0.85),
        ]
    )


def build_card_recognizer() -> PatternRecognizer:
    """Payment card numbers (16 digits, optionally space/dash separated)."""
    return PatternRecognizer(
        supported_entity="CARD_NUMBER",
        patterns=[
            Pattern("Card spaces", r"\b\d{4}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}\b", 0.95),
            Pattern("Card plain",  r"\b\d{16}\b",                                0.75),
        ]
    )


# ── Redaction engine ──────────────────────────────────────────────────────────

class PIIRedactor:
    def __init__(self):
        self.analyzer   = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()

        # Register custom Pakistani recognizers
        self.analyzer.registry.add_recognizer(build_cnic_recognizer())
        self.analyzer.registry.add_recognizer(build_pk_phone_recognizer())
        self.analyzer.registry.add_recognizer(build_card_recognizer())

        # Entities to detect
        self.entities = [
            "PK_CNIC",
            "PK_PHONE",
            "CARD_NUMBER",
            "EMAIL_ADDRESS",
            "PERSON",
        ]

        # Replacement labels
        self.operators = {
            "PK_CNIC":       OperatorConfig("replace", {"new_value": "[CNIC_REDACTED]"}),
            "PK_PHONE":      OperatorConfig("replace", {"new_value": "[PHONE_REDACTED]"}),
            "CARD_NUMBER":   OperatorConfig("replace", {"new_value": "[CARD_REDACTED]"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL_REDACTED]"}),
            "PERSON":        OperatorConfig("replace", {"new_value": "[NAME_REDACTED]"}),
        }

    def redact(self, text: str) -> dict:
        """
        Redact PII from text.

        Returns:
        {
            "original":     str,   # original text (never logged)
            "redacted":     str,   # safe text to pass to LLM/logs
            "pii_detected": list,  # entity types found
            "pii_count":    int,
        }
        """
        results = self.analyzer.analyze(
            text=text,
            entities=self.entities,
            language="en"
        )

        anonymized = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=self.operators
        )

        pii_types = list({r.entity_type for r in results})

        return {
            "original":     text,
            "redacted":     anonymized.text,
            "pii_detected": pii_types,
            "pii_count":    len(results),
        }

    def is_safe(self, text: str) -> bool:
        """Returns True if no PII detected in text."""
        results = self.analyzer.analyze(
            text=text,
            entities=self.entities,
            language="en"
        )
        return len(results) == 0


# ── Singleton instance ────────────────────────────────────────────────────────
_redactor = None

def get_redactor() -> PIIRedactor:
    global _redactor
    if _redactor is None:
        _redactor = PIIRedactor()
    return _redactor


def redact(text: str) -> dict:
    """Convenience function — redact PII from text."""
    return get_redactor().redact(text)
