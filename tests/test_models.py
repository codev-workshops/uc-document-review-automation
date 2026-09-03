"""Tests for document, loan record, and review result models."""

from datetime import datetime

from src.models.document import (
    DocumentMetadata,
    DocumentType,
    ExtractedField,
    ExtractionResult,
    ExtractionStatus,
)
from src.models.loan_record import CorrectionType, LoanCorrectionBatch, LoanCorrectionRecord
from src.models.review_result import (
    FieldComparison,
    MismatchSeverity,
    ReviewDecision,
    ReviewResult,
)


class TestExtractedField:
    def test_high_confidence(self):
        field = ExtractedField(
            field_name="loan_number", field_value="12345", confidence=0.95
        )
        assert field.is_high_confidence is True

    def test_low_confidence(self):
        field = ExtractedField(
            field_name="borrower_name", field_value="John", confidence=0.80
        )
        assert field.is_high_confidence is False

    def test_boundary_confidence(self):
        field = ExtractedField(
            field_name="amount", field_value="100", confidence=0.90
        )
        assert field.is_high_confidence is True


class TestExtractionResult:
    def _make_result(self) -> ExtractionResult:
        return ExtractionResult(
            document_id="doc-001",
            document_type=DocumentType.LOAN_MODIFICATION,
            status=ExtractionStatus.COMPLETED,
            fields=[
                ExtractedField(
                    field_name="loan_number", field_value="12345", confidence=0.99
                ),
                ExtractedField(
                    field_name="borrower_name", field_value="John", confidence=0.85
                ),
                ExtractedField(
                    field_name="amount", field_value="250000", confidence=0.70
                ),
            ],
        )

    def test_low_confidence_fields(self):
        result = self._make_result()
        low = result.low_confidence_fields
        assert len(low) == 2
        assert all(not f.is_high_confidence for f in low)

    def test_get_field_exists(self):
        result = self._make_result()
        field = result.get_field("loan_number")
        assert field is not None
        assert field.field_value == "12345"

    def test_get_field_not_found(self):
        result = self._make_result()
        assert result.get_field("nonexistent") is None


class TestLoanCorrectionRecord:
    def test_record_creation(self):
        record = LoanCorrectionRecord(
            correction_id="corr-001",
            loan_number="12345",
            correction_type=CorrectionType.BORROWER_NAME,
            current_value="Jon Smith",
            proposed_value="John Smith",
            submitted_by="analyst-1",
            submitted_at=datetime(2026, 3, 1, 10, 0),
            borrower_name="John Smith",
            property_address="123 Main St",
        )
        assert record.correction_id == "corr-001"
        assert record.correction_type == CorrectionType.BORROWER_NAME


class TestLoanCorrectionBatch:
    def test_add_record_updates_count(self):
        batch = LoanCorrectionBatch(batch_id="batch-001")
        assert batch.total_count == 0

        record = LoanCorrectionRecord(
            correction_id="corr-001",
            loan_number="12345",
            correction_type=CorrectionType.LOAN_AMOUNT,
            current_value="200000",
            proposed_value="250000",
            submitted_by="analyst-1",
            submitted_at=datetime(2026, 3, 1),
        )
        batch.add_record(record)
        assert batch.total_count == 1
        assert len(batch.records) == 1


class TestReviewResult:
    def _make_comparisons(self) -> list[FieldComparison]:
        return [
            FieldComparison(
                field_name="loan_number",
                document_value="12345",
                record_value="12345",
                is_match=True,
                similarity_score=1.0,
            ),
            FieldComparison(
                field_name="loan_amount",
                document_value="250000",
                record_value="260000",
                is_match=False,
                similarity_score=0.96,
                mismatch_severity=MismatchSeverity.CRITICAL,
            ),
            FieldComparison(
                field_name="borrower_name",
                document_value="Jon Smith",
                record_value="John Smith",
                is_match=False,
                similarity_score=0.90,
                mismatch_severity=MismatchSeverity.WARNING,
            ),
        ]

    def test_mismatch_count(self):
        result = ReviewResult(
            review_id="rev-001",
            correction_id="corr-001",
            loan_number="12345",
            decision=ReviewDecision.MANUAL_REVIEW,
            overall_confidence=0.90,
            field_comparisons=self._make_comparisons(),
        )
        assert result.mismatch_count == 2

    def test_critical_mismatches(self):
        result = ReviewResult(
            review_id="rev-001",
            correction_id="corr-001",
            loan_number="12345",
            decision=ReviewDecision.REJECTED,
            overall_confidence=0.80,
            field_comparisons=self._make_comparisons(),
        )
        criticals = result.critical_mismatches
        assert len(criticals) == 1
        assert criticals[0].field_name == "loan_amount"
