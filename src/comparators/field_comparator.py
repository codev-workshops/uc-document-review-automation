"""Field-level comparison between extracted document data and loan records."""

import logging
from typing import Callable, Iterable, Optional

from src.models.review_result import FieldComparison, MismatchSeverity

logger = logging.getLogger(__name__)

# Fields where exact match is required
EXACT_MATCH_FIELDS = {
    "loan_number",
    "certificate_number",
    "tracking_number",
}

# Fields where minor differences are acceptable
TOLERANT_FIELDS = {
    "borrower_name",
    "property_address",
    "original_borrower",
    "new_borrower",
}

# Fields that are critical for approval decisions
CRITICAL_FIELDS = {
    "loan_number",
    "loan_amount",
    "interest_rate",
    "maturity_date",
    "new_payment_amount",
    "new_interest_rate",
    "coverage_percentage",
}


class FieldComparator:
    """Compares extracted document fields against loan correction records."""

    def __init__(
        self,
        exact_match_fields: Optional[Iterable[str]] = None,
        critical_fields: Optional[Iterable[str]] = None,
        similarity: Optional[Callable[[str, str], float]] = None,
        tolerant_threshold: float = 0.85,
    ) -> None:
        self.exact_match_fields = set(
            EXACT_MATCH_FIELDS if exact_match_fields is None else exact_match_fields
        )
        self.critical_fields = set(
            CRITICAL_FIELDS if critical_fields is None else critical_fields
        )
        self.similarity = similarity or self._fuzzy_similarity
        self.tolerant_threshold = tolerant_threshold

    def compare(
        self,
        field_name: str,
        document_value: str,
        record_value: str,
    ) -> FieldComparison:
        """Compare a single field and return the comparison result."""
        doc_normalized = self._normalize(document_value)
        rec_normalized = self._normalize(record_value)

        if field_name in self.exact_match_fields:
            is_match = doc_normalized == rec_normalized
            similarity = 1.0 if is_match else 0.0
        elif field_name in TOLERANT_FIELDS:
            similarity = self.similarity(doc_normalized, rec_normalized)
            is_match = similarity >= self.tolerant_threshold
        else:
            is_match = doc_normalized == rec_normalized
            similarity = 1.0 if is_match else self.similarity(
                doc_normalized, rec_normalized
            )

        severity: Optional[MismatchSeverity] = None
        if not is_match:
            severity = (
                MismatchSeverity.CRITICAL
                if field_name in self.critical_fields
                else MismatchSeverity.WARNING
            )

        return FieldComparison(
            field_name=field_name,
            document_value=document_value,
            record_value=record_value,
            is_match=is_match,
            similarity_score=similarity,
            mismatch_severity=severity,
        )

    @staticmethod
    def _normalize(value: str) -> str:
        """Normalize a value for comparison (lowercase, strip whitespace)."""
        return " ".join(value.lower().strip().split())

    @staticmethod
    def _fuzzy_similarity(a: str, b: str) -> float:
        """Compute a simple character-level similarity score (Jaccard on bigrams)."""
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0

        bigrams_a = {a[i : i + 2] for i in range(len(a) - 1)}
        bigrams_b = {b[i : i + 2] for i in range(len(b) - 1)}

        if not bigrams_a and not bigrams_b:
            return 1.0 if a == b else 0.0

        intersection = bigrams_a & bigrams_b
        union = bigrams_a | bigrams_b
        return len(intersection) / len(union) if union else 0.0
