"""Decision Agent — determines auto-approval eligibility or routes exceptions."""

import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from src.models.review_result import (
    FieldComparison,
    MismatchSeverity,
    ReviewDecision,
    ReviewResult,
)

logger = logging.getLogger(__name__)

DEFAULT_CONFIDENCE_THRESHOLD = 0.95


class DecisionAgent:
    """Makes approval decisions based on comparison results."""

    def __init__(
        self,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> None:
        self.confidence_threshold = confidence_threshold

    def decide(
        self,
        correction_id: str,
        loan_number: str,
        comparisons: list[FieldComparison],
    ) -> ReviewResult:
        """Evaluate field comparisons and produce a review decision."""
        overall_confidence = self._compute_confidence(comparisons)
        critical_mismatches = [
            c
            for c in comparisons
            if not c.is_match and c.mismatch_severity == MismatchSeverity.CRITICAL
        ]
        any_mismatches = any(not c.is_match for c in comparisons)

        if critical_mismatches:
            decision = ReviewDecision.REJECTED
            escalation_reason = (
                f"{len(critical_mismatches)} critical field mismatch(es): "
                + ", ".join(c.field_name for c in critical_mismatches)
            )
        elif any_mismatches or overall_confidence < self.confidence_threshold:
            decision = ReviewDecision.MANUAL_REVIEW
            escalation_reason = (
                f"Confidence {overall_confidence:.2%} below threshold "
                f"({self.confidence_threshold:.2%})"
                if overall_confidence < self.confidence_threshold
                else "Non-critical field mismatches require human review"
            )
        else:
            decision = ReviewDecision.AUTO_APPROVED
            escalation_reason = None

        result = ReviewResult(
            review_id=f"rev-{uuid4().hex[:8]}",
            correction_id=correction_id,
            loan_number=loan_number,
            decision=decision,
            overall_confidence=overall_confidence,
            field_comparisons=comparisons,
            reviewed_at=datetime.utcnow(),
            escalation_reason=escalation_reason,
        )

        logger.info(
            "Decision for correction %s: %s (confidence=%.2f%%)",
            correction_id,
            decision.value,
            overall_confidence * 100,
        )
        return result

    @staticmethod
    def _compute_confidence(comparisons: list[FieldComparison]) -> float:
        """Compute overall confidence as the weighted average of similarity scores."""
        if not comparisons:
            return 0.0
        return sum(c.similarity_score for c in comparisons) / len(comparisons)
