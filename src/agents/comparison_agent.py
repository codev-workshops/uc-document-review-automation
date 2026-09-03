"""Comparison Agent — validates extracted document data against loan correction records."""

import logging
from typing import Optional

from src.comparators.amount_comparator import AmountComparator
from src.comparators.field_comparator import FieldComparator
from src.comparators.fuzzy_comparator import FuzzyComparator
from src.models.document import ExtractionResult
from src.models.loan_record import LoanCorrectionRecord
from src.models.review_result import FieldComparison, MismatchSeverity

logger = logging.getLogger(__name__)

# Fields that use specialized comparators
NAME_FIELDS = {"borrower_name", "original_borrower", "new_borrower", "recipient_name"}
ADDRESS_FIELDS = {"property_address", "recipient_address"}
AMOUNT_FIELDS = {"loan_amount", "original_amount", "current_balance", "new_payment_amount"}
RATE_FIELDS = {"interest_rate", "new_interest_rate", "coverage_percentage"}


class ComparisonAgent:
    """Compares extracted document fields against loan correction records."""

    def __init__(self) -> None:
        self.field_comparator = FieldComparator()
        self.fuzzy_comparator = FuzzyComparator()
        self.amount_comparator = AmountComparator()

    def compare(
        self,
        extraction: ExtractionResult,
        record: LoanCorrectionRecord,
    ) -> list[FieldComparison]:
        """Compare all extracted fields against the loan correction record."""
        comparisons: list[FieldComparison] = []

        record_fields = self._record_to_fields(record)

        for extracted_field in extraction.fields:
            field_name = extracted_field.field_name
            doc_value = extracted_field.field_value

            record_value = record_fields.get(field_name)
            if record_value is None:
                continue

            comparison = self._compare_field(field_name, doc_value, record_value)
            comparisons.append(comparison)

        logger.info(
            "Comparison complete for correction %s: %d fields, %d mismatches",
            record.correction_id,
            len(comparisons),
            sum(1 for c in comparisons if not c.is_match),
        )
        return comparisons

    def _compare_field(
        self,
        field_name: str,
        doc_value: str,
        record_value: str,
    ) -> FieldComparison:
        """Route a field comparison to the appropriate comparator."""
        if field_name in NAME_FIELDS:
            similarity = self.fuzzy_comparator.compare_names(doc_value, record_value)
            is_match = similarity >= 0.85
        elif field_name in ADDRESS_FIELDS:
            similarity = self.fuzzy_comparator.compare_addresses(doc_value, record_value)
            is_match = similarity >= 0.80
        elif field_name in AMOUNT_FIELDS:
            is_match, similarity = self.amount_comparator.compare_amounts(
                doc_value, record_value
            )
        elif field_name in RATE_FIELDS:
            is_match, similarity = self.amount_comparator.compare_rates(
                doc_value, record_value
            )
        else:
            result = self.field_comparator.compare(field_name, doc_value, record_value)
            return result

        severity: Optional[MismatchSeverity] = None
        if not is_match:
            from src.comparators.field_comparator import CRITICAL_FIELDS

            severity = (
                MismatchSeverity.CRITICAL
                if field_name in CRITICAL_FIELDS
                else MismatchSeverity.WARNING
            )

        return FieldComparison(
            field_name=field_name,
            document_value=doc_value,
            record_value=record_value,
            is_match=is_match,
            similarity_score=similarity,
            mismatch_severity=severity,
        )

    @staticmethod
    def _record_to_fields(record: LoanCorrectionRecord) -> dict[str, str]:
        """Flatten a loan correction record into a field-name → value map."""
        fields: dict[str, str] = {
            "loan_number": record.loan_number,
            "borrower_name": record.borrower_name,
            "property_address": record.property_address,
        }
        if record.loan_amount is not None:
            fields["loan_amount"] = str(record.loan_amount)
        if record.interest_rate is not None:
            fields["interest_rate"] = str(record.interest_rate)
        if record.maturity_date is not None:
            fields["maturity_date"] = record.maturity_date.isoformat()

        # The proposed value maps to the correction-specific field
        fields[record.correction_type.value] = record.proposed_value
        return fields
