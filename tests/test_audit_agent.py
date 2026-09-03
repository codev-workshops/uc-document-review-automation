"""Tests for the Audit Agent."""

import json
import tempfile
from pathlib import Path

from src.agents.audit_agent import AuditAgent
from src.models.review_result import (
    FieldComparison,
    MismatchSeverity,
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
