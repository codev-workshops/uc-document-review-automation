"""Comparison Agent — validates extracted document data against loan correction records."""

import logging
from typing import Optional

from src.comparators.amount_comparator import AmountComparator
from src.comparators.field_comparator import CRITICAL_FIELDS, FieldComparator
from src.comparators.fuzzy_comparator import FuzzyComparator
from src.comparators.strategies import get_address_strategy, get_name_strategy
from src.config.loader import ComparisonConfig, load_comparison_config
from src.models.document import ExtractionResult
from src.models.loan_record import LoanCorrectionRecord
from src.models.review_result import FieldComparison, MismatchSeverity

logger = logging.getLogger(__name__)


class ComparisonAgent:
    """Compares extracted document fields against loan correction records."""

    def __init__(self, config: Optional[ComparisonConfig] = None) -> None:
        self.config = config or load_comparison_config()
        self.field_comparator = FieldComparator()
        self.fuzzy_comparator = FuzzyComparator(
            name_strategy=get_name_strategy(self.config.name_fields.algorithm),
            address_strategy=get_address_strategy(self.config.address_fields.algorithm),
        )
        self.amount_comparator = AmountComparator(tolerance=self.config.amount_tolerance)

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
        cfg = self.config
        if field_name in cfg.name_fields.fields:
            similarity = self.fuzzy_comparator.compare_names(doc_value, record_value)
            is_match = similarity >= cfg.name_fields.threshold
        elif field_name in cfg.address_fields.fields:
            similarity = self.fuzzy_comparator.compare_addresses(doc_value, record_value)
            is_match = similarity >= cfg.address_fields.threshold
        elif field_name in cfg.amount_fields:
            is_match, similarity = self.amount_comparator.compare_amounts(
                doc_value, record_value
            )
        elif field_name in cfg.rate_fields:
            is_match, similarity = self.amount_comparator.compare_rates(
                doc_value, record_value
            )
        else:
            return self.field_comparator.compare(field_name, doc_value, record_value)

        severity: Optional[MismatchSeverity] = None
        if not is_match:
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
