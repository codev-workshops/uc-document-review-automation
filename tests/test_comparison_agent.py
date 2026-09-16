from datetime import date, datetime

import pytest

from src.agents.comparison_agent import CORRECTION_FIELD_NAMES, ComparisonAgent
from src.agents.decision_agent import DecisionAgent
from src.models.document import (
    DocumentType,
    ExtractedField,
    ExtractionResult,
    ExtractionStatus,
)
from src.models.loan_record import CorrectionType, LoanCorrectionRecord
from src.models.review_result import MismatchSeverity, ReviewDecision


def record(correction_type=CorrectionType.LOAN_AMOUNT, proposed_value="250000", **kwargs):
    return LoanCorrectionRecord(
        correction_id="corr-1",
        loan_number="123",
        correction_type=correction_type,
        current_value="old",
        proposed_value=proposed_value,
        submitted_by="tester",
        submitted_at=datetime.now(),
        **kwargs,
    )


def extraction(*fields):
    return ExtractionResult(
        document_id="doc-1",
        document_type=DocumentType.LOAN_MODIFICATION,
        status=ExtractionStatus.COMPLETED,
        fields=[ExtractedField(*field) for field in fields],
    )


class TestComparisonAgent:
    def test_missing_critical_field(self):
        comparisons = ComparisonAgent().compare(
            extraction(("loan_number", "123", 1.0)), record()
        )
        missing = next(c for c in comparisons if c.field_name == "loan_amount")
        assert not missing.is_match
        assert missing.mismatch_severity == MismatchSeverity.CRITICAL
        assert "missing" in missing.notes
        result = DecisionAgent().decide("corr-1", "123", comparisons)
        assert result.decision == ReviewDecision.REJECTED

    def test_missing_noncritical_field(self):
        comparisons = ComparisonAgent().compare(
            extraction(("loan_amount", "250000", 1.0)),
            record(borrower_name="John Smith"),
        )
        missing = next(c for c in comparisons if c.field_name == "borrower_name")
        assert missing.mismatch_severity == MismatchSeverity.WARNING

    def test_confidence_fold(self):
        agent = ComparisonAgent()
        high = agent._compare_field("borrower_name", "John Smith", "John Smith", 0.99)
        low = agent._compare_field("borrower_name", "John Smith", "John Smith", 0.60)
        assert high.similarity_score != low.similarity_score
        assert low.extraction_confidence == 0.60
        assert "low extraction confidence" in low.notes

    @pytest.mark.parametrize("correction_type", list(CorrectionType))
    def test_every_correction_type_is_mapped(self, correction_type):
        key = CORRECTION_FIELD_NAMES[correction_type]
        agent = ComparisonAgent()
        assert agent.route(key) in {"name", "address", "amount", "rate", "date", "field"}

    def test_corrected_field_names(self):
        payment = ComparisonAgent()._record_to_fields(
            record(CorrectionType.PAYMENT_AMOUNT, "100")
        )
        coverage = ComparisonAgent()._record_to_fields(
            record(CorrectionType.MI_COVERAGE, "20")
        )
        assert "new_payment_amount" in payment and "payment_amount" not in payment
        assert "coverage_percentage" in coverage

    def test_proposed_value_overrides_current_value(self):
        fields = ComparisonAgent()._record_to_fields(
            record(
                CorrectionType.BORROWER_NAME,
                "New Name",
                borrower_name="Old Name",
            )
        )
        assert fields["borrower_name"] == "New Name"

    @pytest.mark.parametrize("value", ["01/01/2030", "Jan 1, 2030"])
    def test_date_match(self, value):
        result = ComparisonAgent()._compare_field(
            "maturity_date", value, date(2030, 1, 1).isoformat(), 1.0
        )
        assert result.is_match

    def test_date_mismatch_and_unparseable_info(self):
        mismatch = ComparisonAgent()._compare_field(
            "maturity_date", "2031-01-01", "2030-01-01"
        )
        assert mismatch.mismatch_severity == MismatchSeverity.CRITICAL
        unparseable = ComparisonAgent()._compare_field("loan_amount", "N/A", "250000")
        assert unparseable.mismatch_severity == MismatchSeverity.INFO
        assert DecisionAgent().decide("corr-1", "123", [unparseable]).decision == ReviewDecision.MANUAL_REVIEW
