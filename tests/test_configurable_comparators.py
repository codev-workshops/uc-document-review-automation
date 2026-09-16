from datetime import datetime

from src.agents.audit_agent import AuditAgent
from src.comparators.amount_comparator import ComparisonStatus, AmountComparator
from src.comparators.date_comparator import DateComparator
from src.comparators.fuzzy_comparator import FuzzyComparator
from src.models.review_result import ReviewDecision, ReviewResult


class TestConfigurableComparators:
    def test_fuzzy_algorithms_and_overrides(self):
        assert FuzzyComparator("levenshtein").compare_text(
            "John Smith", "Jon Smith"
        ) > 0.85
        assert FuzzyComparator("hybrid").compare_names("John Smth", "John Smith") > 0.8
        assert FuzzyComparator().compare_names("Mr. John Smith", "John Smith") == 1.0
        assert FuzzyComparator(name_noise={"esq"}).compare_names(
            "John Smith Esq", "John Smith"
        ) == 1.0
        assert FuzzyComparator(address_abbreviations={"highway": "hwy"}).compare_addresses(
            "1 Main Highway", "1 Main Hwy"
        ) == 1.0

    def test_amount_rate_and_date_details(self):
        amount = AmountComparator()
        result = amount.compare_amounts_detailed("$500,000.00", "$500,000.50")
        assert not result.is_match and result.similarity < 1.0
        assert AmountComparator(relative_tolerance=0.001).compare_amounts(
            "500000", "500000.50"
        )[0]
        assert amount.compare_amounts_detailed("N/A", "1").status is ComparisonStatus.UNPARSEABLE
        for left, right in (("3.5%", "3.5"), ("3.5", "0.035"), ("25", "0.25")):
            assert amount.compare_rates(left, right)[0]
        assert amount.compare_rates("3.5", "4.0")[1] < 1.0

        dates = DateComparator()
        values = ["01/01/2030", "2030-01-01", "Jan 1, 2030", "January 1, 2030"]
        assert all(dates.compare(values[0], value).is_match for value in values)
        assert not dates.compare(values[0], "2031-01-01").is_match
        assert dates.compare("someday", values[0]).status is ComparisonStatus.UNPARSEABLE


class TestAuditQueries:
    def test_typed_ids_and_query_filters(self, tmp_path):
        agent = AuditAgent(str(tmp_path / "audit.jsonl"))
        extraction = agent.log_extraction("doc-1", "pdf", 1, "completed")
        comparison = agent.log_comparison("rev-1", "corr-1", 1, 0)
        result = ReviewResult(
            review_id="rev-1", correction_id="corr-1", loan_number="loan-1",
            decision=ReviewDecision.AUTO_APPROVED, overall_confidence=0.8,
        )
        decision = agent.log_decision(result)
        assert extraction.document_id == "doc-1"
        assert comparison.correction_id == "corr-1"
        assert decision.loan_number == "loan-1"
        assert len(agent.get_entries_by_action("review_decision")) == 1
        assert agent.get_entries_by_decision(ReviewDecision.AUTO_APPROVED) == [decision]
        assert agent.get_low_confidence_entries(0.9) == [decision]
        assert agent.get_entries_by_loan_number("loan-1") == [decision]

    def test_disk_entries_are_read_only_and_deduplicated(self, tmp_path):
        path = tmp_path / "audit.jsonl"
        path.write_text(
            '{"audit_id":"old-1","review_id":"r","action":"x","timestamp":"2020-01-01T00:00:00",'
            '"agent_name":"Old","input_summary":"","output_summary":"","decision":null,"confidence":null,"metadata":{}}\n'
            "\n"
        )
        agent = AuditAgent(str(path))
        before = list(agent.entries)
        agent.log_extraction("doc-1", "pdf", 1, "completed")
        assert len(agent.load_persisted_entries()) == 2
        assert agent.entries != before
        assert len(agent.query_entries(include_persisted=True)) == 2
        assert len(agent.query_entries()) == 1
