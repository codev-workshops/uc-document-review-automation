"""Audit Agent — logs all AI decisions and comparisons for compliance."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from src.models.review_result import AuditEntry, ReviewDecision, ReviewResult

logger = logging.getLogger(__name__)


class AuditAgent:
    """Provides immutable audit logging for all document review decisions."""

    def __init__(self, log_path: Optional[str] = None) -> None:
        self.log_path = Path(log_path) if log_path else Path("logs/audit.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.entries: list[AuditEntry] = []

    def log_extraction(
        self,
        document_id: str,
        document_type: str,
        field_count: int,
        status: str,
    ) -> AuditEntry:
        """Log a document extraction event."""
        entry = AuditEntry(
            audit_id=f"aud-{uuid4().hex[:8]}",
            review_id="",
            action="document_extraction",
            timestamp=datetime.utcnow(),
            agent_name="DocumentExtractionAgent",
            input_summary=f"document_id={document_id}, type={document_type}",
            output_summary=f"fields_extracted={field_count}, status={status}",
        )
        self._persist(entry)
        return entry

    def log_comparison(
        self,
        review_id: str,
        correction_id: str,
        total_fields: int,
        mismatches: int,
    ) -> AuditEntry:
        """Log a field comparison event."""
        entry = AuditEntry(
            audit_id=f"aud-{uuid4().hex[:8]}",
            review_id=review_id,
            action="field_comparison",
            timestamp=datetime.utcnow(),
            agent_name="ComparisonAgent",
            input_summary=f"correction_id={correction_id}",
            output_summary=f"total_fields={total_fields}, mismatches={mismatches}",
        )
        self._persist(entry)
        return entry

    def log_decision(self, result: ReviewResult) -> AuditEntry:
        """Log a review decision event."""
        entry = AuditEntry(
            audit_id=f"aud-{uuid4().hex[:8]}",
            review_id=result.review_id,
            action="review_decision",
            timestamp=datetime.utcnow(),
            agent_name="DecisionAgent",
            input_summary=(
                f"correction_id={result.correction_id}, "
                f"loan={result.loan_number}"
            ),
            output_summary=(
                f"decision={result.decision.value}, "
                f"confidence={result.overall_confidence:.4f}"
            ),
            decision=result.decision,
            confidence=result.overall_confidence,
            metadata={
                "mismatch_count": str(result.mismatch_count),
                "escalation_reason": result.escalation_reason or "",
            },
        )
        self._persist(entry)
        return entry

    def _persist(self, entry: AuditEntry) -> None:
        """Append an audit entry to the log file and in-memory list."""
        self.entries.append(entry)
        record = {
            "audit_id": entry.audit_id,
            "review_id": entry.review_id,
            "action": entry.action,
            "timestamp": entry.timestamp.isoformat(),
            "agent_name": entry.agent_name,
            "input_summary": entry.input_summary,
            "output_summary": entry.output_summary,
            "decision": entry.decision.value if entry.decision else None,
            "confidence": entry.confidence,
            "metadata": entry.metadata,
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(record) + "\n")

    def get_entries_for_review(self, review_id: str) -> list[AuditEntry]:
        """Retrieve all audit entries for a specific review."""
        return [e for e in self.entries if e.review_id == review_id]
