"""Tests for the Decision Agent."""

from src.agents.decision_agent import DecisionAgent
from src.models.review_result import (
    FieldComparison,
    MismatchSeverity,
    ReviewDecision,
)


class TestDecisionAgent:
    def setup_method(self):
        self.agent = DecisionAgent(confidence_threshold=0.95)

    def _matching_comparisons(self) -> list[FieldComparison]:
        return [
            FieldComparison(
                field_name="loan_number",
                document_value="12345",
                record_value="12345",
                is_match=True,
                similarity_score=1.0,
            ),
            FieldComparison(
                field_name="borrower_name",
                document_value="John Smith",
                record_value="John Smith",
                is_match=True,
                similarity_score=1.0,
            ),
            FieldComparison(
                field_name="loan_amount",
                document_value="250000",
                record_value="250000",
                is_match=True,
                similarity_score=1.0,
            ),
        ]

    def test_auto_approve_all_match(self):
        result = self.agent.decide("corr-001", "12345", self._matching_comparisons())
        assert result.decision == ReviewDecision.AUTO_APPROVED
        assert result.overall_confidence == 1.0
        assert result.escalation_reason is None

    def test_reject_on_critical_mismatch(self):
        comparisons = [
            FieldComparison(
                field_name="loan_number",
                document_value="12345",
                record_value="67890",
                is_match=False,
                similarity_score=0.0,
                mismatch_severity=MismatchSeverity.CRITICAL,
            ),
        ]
        result = self.agent.decide("corr-002", "12345", comparisons)
        assert result.decision == ReviewDecision.REJECTED
        assert "critical" in result.escalation_reason.lower()

    def test_manual_review_on_warning_mismatch(self):
        comparisons = [
            FieldComparison(
                field_name="loan_number",
                document_value="12345",
                record_value="12345",
                is_match=True,
                similarity_score=1.0,
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
        result = self.agent.decide("corr-003", "12345", comparisons)
        assert result.decision == ReviewDecision.MANUAL_REVIEW

    def test_manual_review_on_low_confidence(self):
        comparisons = [
            FieldComparison(
                field_name="loan_number",
                document_value="12345",
                record_value="12345",
                is_match=True,
                similarity_score=0.80,
            ),
        ]
        result = self.agent.decide("corr-004", "12345", comparisons)
        assert result.decision == ReviewDecision.MANUAL_REVIEW
        assert "confidence" in result.escalation_reason.lower()

    def test_empty_comparisons(self):
        result = self.agent.decide("corr-005", "12345", [])
        assert result.overall_confidence == 0.0
        assert result.decision == ReviewDecision.MANUAL_REVIEW

    def test_review_id_generated(self):
        result = self.agent.decide("corr-006", "12345", self._matching_comparisons())
        assert result.review_id.startswith("rev-")

    def test_correction_id_preserved(self):
        result = self.agent.decide("corr-007", "99999", self._matching_comparisons())
        assert result.correction_id == "corr-007"
        assert result.loan_number == "99999"
