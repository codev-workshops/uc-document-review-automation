"""Models for document review decisions."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ReviewDecision(Enum):
    AUTO_APPROVED = "auto_approved"
    MANUAL_REVIEW = "manual_review"
    REJECTED = "rejected"


class MismatchSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class FieldComparison:
    """Result of comparing a single extracted field against the loan record."""

    field_name: str
    document_value: str
    record_value: str
    is_match: bool
    similarity_score: float
    mismatch_severity: Optional[MismatchSeverity] = None
    notes: str = ""


@dataclass
class ReviewResult:
    """The complete review result for a loan correction."""

    review_id: str
    correction_id: str
    loan_number: str
    decision: ReviewDecision
    overall_confidence: float
    field_comparisons: list[FieldComparison] = field(default_factory=list)
    reviewed_at: datetime = field(default_factory=datetime.utcnow)
    reviewer_notes: str = ""
    escalation_reason: Optional[str] = None

    @property
    def mismatch_count(self) -> int:
        return sum(1 for fc in self.field_comparisons if not fc.is_match)

    @property
    def critical_mismatches(self) -> list[FieldComparison]:
        return [
            fc
            for fc in self.field_comparisons
            if not fc.is_match
            and fc.mismatch_severity == MismatchSeverity.CRITICAL
        ]


@dataclass
class AuditEntry:
    """Immutable audit log entry for compliance."""

    audit_id: str
    review_id: str
    action: str
    timestamp: datetime
    agent_name: str
    input_summary: str
    output_summary: str
    decision: Optional[ReviewDecision] = None
    confidence: Optional[float] = None
    metadata: dict[str, str] = field(default_factory=dict)
