"""Tests for the Audit Agent."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from src.agents.audit_agent import AuditAgent
from src.models.review_result import (
    FieldComparison,
    ReviewDecision,
    ReviewResult,
)


class TestAuditAgent:
    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.log_path = str(Path(self.tmp_dir) / "audit.jsonl")
        self.agent = AuditAgent(log_path=self.log_path)

    def test_log_extraction(self):
        entry = self.agent.log_extraction(
            document_id="doc-001",
            document_type="loan_modification",
            field_count=5,
            status="completed",
        )
        assert entry.audit_id.startswith("aud-")
        assert entry.action == "document_extraction"
        assert entry.agent_name == "DocumentExtractionAgent"
        assert "doc-001" in entry.input_summary

    def test_log_comparison(self):
        entry = self.agent.log_comparison(
            review_id="rev-001",
            correction_id="corr-001",
            total_fields=6,
            mismatches=1,
        )
        assert entry.action == "field_comparison"
        assert entry.review_id == "rev-001"
        assert "corr-001" in entry.input_summary

    def test_log_decision(self):
        result = ReviewResult(
            review_id="rev-001",
            correction_id="corr-001",
            loan_number="12345",
            decision=ReviewDecision.AUTO_APPROVED,
            overall_confidence=0.98,
            field_comparisons=[
                FieldComparison(
                    field_name="loan_number",
                    document_value="12345",
                    record_value="12345",
                    is_match=True,
                    similarity_score=1.0,
                ),
            ],
        )
        entry = self.agent.log_decision(result)
        assert entry.action == "review_decision"
        assert entry.decision == ReviewDecision.AUTO_APPROVED
        assert entry.confidence == 0.98

    def test_entries_persisted_to_file(self):
        self.agent.log_extraction("doc-001", "pdf", 3, "completed")
        self.agent.log_extraction("doc-002", "image", 2, "failed")

        with open(self.log_path) as f:
            lines = f.readlines()

        assert len(lines) == 2
        record = json.loads(lines[0])
        assert record["action"] == "document_extraction"

    def test_get_entries_for_review(self):
        self.agent.log_comparison("rev-001", "corr-001", 5, 0)
        self.agent.log_comparison("rev-002", "corr-002", 3, 1)
        self.agent.log_comparison("rev-001", "corr-003", 4, 2)

        entries = self.agent.get_entries_for_review("rev-001")
        assert len(entries) == 2
        assert all(e.review_id == "rev-001" for e in entries)

    def test_in_memory_list_tracks_all_entries(self):
        self.agent.log_extraction("doc-001", "pdf", 3, "completed")
        self.agent.log_comparison("rev-001", "corr-001", 5, 0)
        assert len(self.agent.entries) == 2

    def test_typed_ids_are_persisted(self):
        extraction = self.agent.log_extraction("doc-001", "pdf", 3, "completed")
        comparison = self.agent.log_comparison("rev-001", "corr-001", 5, 0)
        result = ReviewResult(
            review_id="rev-001",
            correction_id="corr-001",
            loan_number="loan-001",
            decision=ReviewDecision.AUTO_APPROVED,
            overall_confidence=0.98,
        )
        decision = self.agent.log_decision(result)
        records = [json.loads(line) for line in Path(self.log_path).read_text().splitlines()]
        assert extraction.document_id == "doc-001"
        assert comparison.correction_id == "corr-001"
        assert decision.loan_number == "loan-001"
        assert records[0]["document_id"] == "doc-001"
        assert records[1]["correction_id"] == "corr-001"
        assert records[2]["correction_id"] == "corr-001"
        assert records[2]["loan_number"] == "loan-001"

    def test_get_entries_by_decision(self):
        result = ReviewResult(
            review_id="rev-001",
            correction_id="corr-001",
            loan_number="loan-001",
            decision=ReviewDecision.AUTO_APPROVED,
            overall_confidence=0.98,
        )
        entry = self.agent.log_decision(result)
        assert self.agent.get_entries_by_decision(ReviewDecision.AUTO_APPROVED) == [entry]

    def test_get_entries_by_action(self):
        entry = self.agent.log_comparison("rev-001", "corr-001", 5, 0)
        assert self.agent.get_entries_by_action("field_comparison") == [entry]

    def test_get_entries_by_agent(self):
        entry = self.agent.log_extraction("doc-001", "pdf", 3, "completed")
        assert self.agent.get_entries_by_agent("DocumentExtractionAgent") == [entry]

    def test_low_confidence_excludes_entries_without_confidence(self):
        self.agent.log_extraction("doc-001", "pdf", 3, "completed")
        self.agent.log_comparison("rev-001", "corr-001", 5, 0)
        result = ReviewResult(
            review_id="rev-001",
            correction_id="corr-001",
            loan_number="loan-001",
            decision=ReviewDecision.MANUAL_REVIEW,
            overall_confidence=0.8,
        )
        entry = self.agent.log_decision(result)
        assert self.agent.get_low_confidence_entries(0.9) == [entry]

    def test_get_entries_in_range(self):
        start = datetime.utcnow() - timedelta(seconds=1)
        entry = self.agent.log_comparison("rev-001", "corr-001", 5, 0)
        end = datetime.utcnow() + timedelta(seconds=1)
        assert self.agent.get_entries_in_range(start, end) == [entry]

    def test_compound_query_filters(self):
        result = ReviewResult(
            review_id="rev-001",
            correction_id="corr-001",
            loan_number="loan-001",
            decision=ReviewDecision.AUTO_APPROVED,
            overall_confidence=0.8,
        )
        entry = self.agent.log_decision(result)
        assert self.agent.query_entries(
            decision=ReviewDecision.AUTO_APPROVED,
            max_confidence=0.9,
        ) == [entry]

    def test_get_entries_by_loan_number(self):
        result = ReviewResult(
            review_id="rev-001",
            correction_id="corr-001",
            loan_number="loan-001",
            decision=ReviewDecision.AUTO_APPROVED,
            overall_confidence=0.98,
        )
        entry = self.agent.log_decision(result)
        assert self.agent.get_entries_by_loan_number("loan-001") == [entry]

    def test_disk_backed_queries_and_read_only_load(self):
        old_line = {
            "audit_id": "old-1",
            "review_id": "old-review",
            "action": "old_action",
            "timestamp": "2020-01-01T00:00:00",
            "agent_name": "OldAgent",
            "input_summary": "",
            "output_summary": "",
            "decision": None,
            "confidence": None,
            "metadata": {},
        }
        Path(self.log_path).write_text(json.dumps(old_line) + "\n\n")
        self.agent.log_extraction("doc-001", "pdf", 3, "completed")
        before_entries = list(self.agent.entries)
        before_bytes = Path(self.log_path).read_bytes()
        assert len(self.agent.query_entries(include_persisted=True)) == 2
        assert len(self.agent.query_entries()) == 1
        assert self.agent.load_persisted_entries()[0].document_id is None
        assert self.agent.entries == before_entries
        assert Path(self.log_path).read_bytes() == before_bytes
