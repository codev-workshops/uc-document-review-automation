from datetime import date, datetime

from src.agents.comparison_agent import ComparisonAgent
from src.agents.decision_agent import DecisionAgent
from src.models.document import DocumentType, ExtractedField, ExtractionResult, ExtractionStatus
from src.models.loan_record import CorrectionType, LoanCorrectionRecord
from src.models.review_result import ReviewDecision, ReviewResult


def run_pipeline(fields, record):
    extraction = ExtractionResult(
        document_id="doc-1",
        document_type=DocumentType.LOAN_MODIFICATION,
        status=ExtractionStatus.COMPLETED,
        fields=[ExtractedField(name, value, confidence) for name, value, confidence in fields],
    )
    comparisons = ComparisonAgent().compare(extraction, record)
    return DecisionAgent().decide(record.correction_id, record.loan_number, comparisons)


def make_record(**kwargs):
    return LoanCorrectionRecord(
        correction_id="corr-1", loan_number="123",
        correction_type=kwargs.pop("correction_type", CorrectionType.LOAN_AMOUNT),
        current_value="old", proposed_value=kwargs.pop("proposed_value", "250000"),
        submitted_by="tester", submitted_at=datetime.now(), **kwargs,
    )


class TestPipeline:
    def test_golden_cases(self):
        base = [
            ("loan_number", "123", 1.0), ("borrower_name", "John Smith", 1.0),
            ("loan_amount", "250000", 1.0),
        ]
        matching_record = make_record(borrower_name="John Smith")
        assert run_pipeline(base, matching_record).decision == ReviewDecision.AUTO_APPROVED
        typo = [(name, "Jon Smith" if name == "borrower_name" else value, confidence)
                for name, value, confidence in base]
        assert run_pipeline(typo, matching_record).decision == ReviewDecision.MANUAL_REVIEW
        date_record = make_record(
            correction_type=CorrectionType.BORROWER_NAME,
            proposed_value="John Smith", maturity_date=date(2030, 1, 1),
        )
        date_fields = [
            ("loan_number", "123", 1.0), ("borrower_name", "John Smith", 1.0),
            ("maturity_date", "01/01/2030", 1.0),
        ]
        assert run_pipeline(date_fields, date_record).decision == ReviewDecision.AUTO_APPROVED

    def test_missing_unparseable_and_wrong_amounts(self):
        clean = [("loan_number", "123", 1.0), ("loan_amount", "250000", 1.0)]
        assert run_pipeline(clean, make_record()).decision == ReviewDecision.AUTO_APPROVED
        assert run_pipeline([("loan_number", "123", 1.0)], make_record()).decision == ReviewDecision.REJECTED
        assert run_pipeline(
            [("loan_number", "123", 1.0), ("loan_amount", "N/A", 1.0)],
            make_record(),
        ).decision == ReviewDecision.MANUAL_REVIEW
        assert run_pipeline(
            [("loan_number", "123", 1.0), ("loan_amount", "1", 1.0)],
            make_record(),
        ).decision == ReviewDecision.REJECTED
