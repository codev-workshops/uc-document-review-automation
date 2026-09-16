"""Audit Agent — logs all AI decisions and comparisons for compliance."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
from uuid import uuid4

from src.models.review_result import AuditEntry, ReviewDecision, ReviewResult

logger = logging.getLogger(__name__)


class AuditAgent:
    """Provides immutable audit logging for all document review decisions."""

    def __init__(self, log_path: Optional[str] = None) -> None:
        self.log_path = Path(log_path) if log_path else Path("logs/audit.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.entries: list[AuditEntry] = []

    def log_extraction(self, document_id, document_type, field_count, status) -> AuditEntry:
        entry = AuditEntry(
            audit_id=f"aud-{uuid4().hex[:8]}", review_id="", action="document_extraction",
            timestamp=datetime.utcnow(), agent_name="DocumentExtractionAgent",
            input_summary=f"document_id={document_id}, type={document_type}",
            output_summary=f"fields_extracted={field_count}, status={status}",
            document_id=document_id,
        )
        self._persist(entry)
        return entry

    def log_comparison(self, review_id, correction_id, total_fields, mismatches) -> AuditEntry:
        entry = AuditEntry(
            audit_id=f"aud-{uuid4().hex[:8]}", review_id=review_id, action="field_comparison",
            timestamp=datetime.utcnow(), agent_name="ComparisonAgent",
            input_summary=f"correction_id={correction_id}",
            output_summary=f"total_fields={total_fields}, mismatches={mismatches}",
            correction_id=correction_id,
        )
        self._persist(entry)
        return entry

    def log_decision(self, result: ReviewResult) -> AuditEntry:
        entry = AuditEntry(
            audit_id=f"aud-{uuid4().hex[:8]}", review_id=result.review_id,
            action="review_decision", timestamp=datetime.utcnow(), agent_name="DecisionAgent",
            input_summary=f"correction_id={result.correction_id}, loan={result.loan_number}",
            output_summary=f"decision={result.decision.value}, confidence={result.overall_confidence:.4f}",
            decision=result.decision, confidence=result.overall_confidence,
            metadata={
                "mismatch_count": str(result.mismatch_count),
                "escalation_reason": result.escalation_reason or "",
            },
            correction_id=result.correction_id, loan_number=result.loan_number,
        )
        self._persist(entry)
        return entry

    def _persist(self, entry: AuditEntry) -> None:
        self.entries.append(entry)
        record = {
            "audit_id": entry.audit_id, "review_id": entry.review_id, "action": entry.action,
            "timestamp": entry.timestamp.isoformat(), "agent_name": entry.agent_name,
            "input_summary": entry.input_summary, "output_summary": entry.output_summary,
            "decision": entry.decision.value if entry.decision else None,
            "confidence": entry.confidence, "metadata": entry.metadata,
            "loan_number": entry.loan_number, "correction_id": entry.correction_id,
            "document_id": entry.document_id,
        }
        with self.log_path.open("a") as stream:
            stream.write(json.dumps(record) + "\n")

    @staticmethod
    def _entry_from_record(record: dict) -> AuditEntry:
        decision = record.get("decision")
        return AuditEntry(
            audit_id=record["audit_id"], review_id=record["review_id"],
            action=record["action"], timestamp=datetime.fromisoformat(record["timestamp"]),
            agent_name=record["agent_name"], input_summary=record["input_summary"],
            output_summary=record["output_summary"],
            decision=ReviewDecision(decision) if decision is not None else None,
            confidence=record.get("confidence"), metadata=record.get("metadata", {}),
            loan_number=record.get("loan_number"), correction_id=record.get("correction_id"),
            document_id=record.get("document_id"),
        )

    def load_persisted_entries(self) -> list[AuditEntry]:
        if not self.log_path.exists():
            return []
        with self.log_path.open() as stream:
            return [
                self._entry_from_record(json.loads(line))
                for line in stream if line.strip()
            ]

    def _all_entries(self, include_persisted: bool) -> list[AuditEntry]:
        if not include_persisted:
            return list(self.entries)
        persisted = self.load_persisted_entries()
        known = {entry.audit_id for entry in persisted}
        return persisted + [entry for entry in self.entries if entry.audit_id not in known]

    def query_entries(
        self, *, decision: Optional[ReviewDecision] = None, action: Optional[str] = None,
        agent_name: Optional[str] = None, min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None, start: Optional[datetime] = None,
        end: Optional[datetime] = None, loan_number=None, correction_id=None,
        document_id=None, review_id=None, predicate: Optional[Callable[[AuditEntry], bool]] = None,
        include_persisted: bool = False,
    ) -> list[AuditEntry]:
        entries = self._all_entries(include_persisted)
        return [
            entry for entry in entries
            if (decision is None or entry.decision == decision)
            and (action is None or entry.action == action)
            and (agent_name is None or entry.agent_name == agent_name)
            and (min_confidence is None or (
                entry.confidence is not None and entry.confidence >= min_confidence
            ))
            and (max_confidence is None or (
                entry.confidence is not None and entry.confidence < max_confidence
            ))
            and (start is None or entry.timestamp >= start)
            and (end is None or entry.timestamp <= end)
            and (loan_number is None or entry.loan_number == loan_number)
            and (correction_id is None or entry.correction_id == correction_id)
            and (document_id is None or entry.document_id == document_id)
            and (review_id is None or entry.review_id == review_id)
            and (predicate is None or predicate(entry))
        ]

    def get_entries_by_decision(self, decision, include_persisted=False):
        return self.query_entries(decision=decision, include_persisted=include_persisted)

    def get_low_confidence_entries(self, threshold, include_persisted=False):
        return self.query_entries(max_confidence=threshold, include_persisted=include_persisted)

    def get_entries_by_action(self, action, include_persisted=False):
        return self.query_entries(action=action, include_persisted=include_persisted)

    def get_entries_by_agent(self, agent_name, include_persisted=False):
        return self.query_entries(agent_name=agent_name, include_persisted=include_persisted)

    def get_entries_in_range(self, start, end, include_persisted=False):
        return self.query_entries(start=start, end=end, include_persisted=include_persisted)

    def get_entries_by_loan_number(self, loan_number, include_persisted=False):
        return self.query_entries(loan_number=loan_number, include_persisted=include_persisted)

    def get_entries_for_review(self, review_id: str) -> list[AuditEntry]:
        return [entry for entry in self.entries if entry.review_id == review_id]
