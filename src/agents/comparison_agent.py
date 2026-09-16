"""Comparison Agent — validates extracted document data against loan correction records."""

import logging
from pathlib import Path
from typing import Optional

from src.comparators.amount_comparator import AmountComparator, ComparisonStatus
from src.comparators.date_comparator import DateComparator
from src.comparators.field_comparator import (
    CRITICAL_FIELDS,
    EXACT_MATCH_FIELDS,
    FieldComparator,
)
from src.comparators.field_sets import (
    ADDRESS_FIELDS,
    AMOUNT_FIELDS,
    DATE_FIELDS,
    NAME_FIELDS,
    RATE_FIELDS,
)
from src.comparators.fuzzy_comparator import FuzzyComparator
from src.models.document import ExtractionResult
from src.models.loan_record import CorrectionType, LoanCorrectionRecord
from src.models.review_result import FieldComparison, MismatchSeverity
from src.utils.config import ComparisonConfig, load_comparison_config

logger = logging.getLogger(__name__)

CORRECTION_FIELD_NAMES: dict[CorrectionType, str] = {
    CorrectionType.BORROWER_NAME: "borrower_name",
    CorrectionType.PROPERTY_ADDRESS: "property_address",
    CorrectionType.LOAN_AMOUNT: "loan_amount",
    CorrectionType.INTEREST_RATE: "interest_rate",
    CorrectionType.MATURITY_DATE: "maturity_date",
    CorrectionType.PAYMENT_AMOUNT: "new_payment_amount",
    CorrectionType.MI_COVERAGE: "coverage_percentage",
    CorrectionType.LOAN_TYPE: "loan_type",
    CorrectionType.OCCUPANCY_STATUS: "occupancy_status",
}


class ComparisonAgent:
    """Compares extracted document fields against loan correction records."""

    def __init__(self, config: Optional[ComparisonConfig | str | Path] = None) -> None:
        cfg = (
            ComparisonConfig.default()
            if config is None
            else load_comparison_config(config)
            if isinstance(config, (str, Path))
            else config
        )
        self.config = cfg
        self.fuzzy_comparator = FuzzyComparator(
            algorithm=cfg.fuzzy_match.algorithm,
            name_threshold=cfg.fuzzy_match.name_fields.threshold,
            address_threshold=cfg.fuzzy_match.address_fields.threshold,
            name_noise=cfg.fuzzy_match.name_noise,
            address_abbreviations=cfg.fuzzy_match.address_abbreviations,
        )
        self.amount_comparator = AmountComparator(
            tolerance=cfg.amount_fields.tolerance,
            relative_tolerance=cfg.amount_fields.relative_tolerance,
            rate_tolerance=cfg.rate_fields.tolerance,
        )
        self.field_comparator = FieldComparator(
            exact_match_fields=cfg.exact_match_fields,
            critical_fields=cfg.critical_fields,
            similarity=self.fuzzy_comparator.compare_text,
        )
        self.date_comparator = DateComparator()
        self.name_fields = cfg.fuzzy_match.name_fields.fields
        self.address_fields = cfg.fuzzy_match.address_fields.fields
        self.amount_fields = cfg.amount_fields.fields
        self.rate_fields = cfg.rate_fields.fields
        self.date_fields = cfg.date_fields
        self.critical_fields = cfg.critical_fields

    def route(self, field_name: str) -> str:
        if field_name in self.name_fields:
            return "name"
        if field_name in self.address_fields:
            return "address"
        if field_name in self.amount_fields:
            return "amount"
        if field_name in self.rate_fields:
            return "rate"
        if field_name in self.date_fields:
            return "date"
        return "field"

    def compare(
        self,
        extraction: ExtractionResult,
        record: LoanCorrectionRecord,
    ) -> list[FieldComparison]:
        comparisons: list[FieldComparison] = []
        record_fields = self._record_to_fields(record)
        for field_name, record_value in record_fields.items():
            extracted = extraction.get_field(field_name)
            if extracted is None:
                comparisons.append(
                    FieldComparison(
                        field_name=field_name,
                        document_value="",
                        record_value=record_value,
                        is_match=False,
                        similarity_score=0.0,
                        mismatch_severity=(
                            MismatchSeverity.CRITICAL
                            if field_name in self.critical_fields
                            else MismatchSeverity.WARNING
                        ),
                        notes="field missing from document",
                    )
                )
            else:
                comparisons.append(
                    self._compare_field(
                        field_name,
                        extracted.field_value,
                        record_value,
                        extracted.confidence,
                    )
                )
        logger.info(
            "Comparison complete for correction %s: %d fields, %d mismatches",
            record.correction_id,
            len(comparisons),
            sum(1 for comparison in comparisons if not comparison.is_match),
        )
        return comparisons

    def _compare_field(
        self,
        field_name: str,
        doc_value: str,
        record_value: str,
        confidence: Optional[float] = None,
    ) -> FieldComparison:
        route = self.route(field_name)
        notes: list[str] = []
        extraction_confidence = confidence
        if route == "name":
            similarity = self.fuzzy_comparator.compare_names(doc_value, record_value)
            is_match = similarity >= self.fuzzy_comparator.name_threshold
            severity = self._severity(field_name, is_match)
        elif route == "address":
            similarity = self.fuzzy_comparator.compare_addresses(doc_value, record_value)
            is_match = similarity >= self.fuzzy_comparator.address_threshold
            severity = self._severity(field_name, is_match)
        elif route == "amount":
            result = self.amount_comparator.compare_amounts_detailed(doc_value, record_value)
            is_match, similarity, severity = self._numeric_result(field_name, result, notes)
        elif route == "rate":
            result = self.amount_comparator.compare_rates_detailed(doc_value, record_value)
            is_match, similarity, severity = self._numeric_result(field_name, result, notes)
        elif route == "date":
            result = self.date_comparator.compare(doc_value, record_value)
            is_match, similarity, severity = self._numeric_result(field_name, result, notes)
        else:
            result = self.field_comparator.compare(field_name, doc_value, record_value)
            is_match = result.is_match
            similarity = result.similarity_score
            severity = result.mismatch_severity

        if confidence is not None and confidence < self.config.low_confidence_threshold:
            similarity *= confidence
            notes.append(f"low extraction confidence ({confidence:.2f})")
        return FieldComparison(
            field_name=field_name,
            document_value=doc_value,
            record_value=record_value,
            is_match=is_match,
            similarity_score=similarity,
            mismatch_severity=severity,
            notes="; ".join(notes),
            extraction_confidence=extraction_confidence,
        )

    def _numeric_result(self, field_name, result, notes):
        if result.status is ComparisonStatus.UNPARSEABLE:
            notes.append("unparseable value; requires manual review")
            return False, 0.0, MismatchSeverity.INFO
        return result.is_match, result.similarity, self._severity(field_name, result.is_match)

    def _severity(
        self, field_name: str, is_match: bool
    ) -> Optional[MismatchSeverity]:
        if is_match:
            return None
        return (
            MismatchSeverity.CRITICAL
            if field_name in self.critical_fields
            else MismatchSeverity.WARNING
        )

    @staticmethod
    def _record_to_fields(record: LoanCorrectionRecord) -> dict[str, str]:
        """Emit base values first, then explicitly override the proposed correction field."""
        fields: dict[str, str] = {"loan_number": record.loan_number}
        if record.borrower_name:
            fields["borrower_name"] = record.borrower_name
        if record.property_address:
            fields["property_address"] = record.property_address
        if record.loan_amount is not None:
            fields["loan_amount"] = str(record.loan_amount)
        if record.interest_rate is not None:
            fields["interest_rate"] = str(record.interest_rate)
        if record.maturity_date is not None:
            fields["maturity_date"] = record.maturity_date.isoformat()
        target = CORRECTION_FIELD_NAMES[record.correction_type]
        fields[target] = record.proposed_value
        return fields


NAME_FIELDS = NAME_FIELDS
ADDRESS_FIELDS = ADDRESS_FIELDS
AMOUNT_FIELDS = AMOUNT_FIELDS
RATE_FIELDS = RATE_FIELDS
DATE_FIELDS = DATE_FIELDS
