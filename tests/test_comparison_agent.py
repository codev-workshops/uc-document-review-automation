"""Tests for the Comparison Agent."""

from datetime import date

import pytest

from src.agents.comparison_agent import (
    ADDRESS_FIELDS,
    AMOUNT_FIELDS,
    NAME_FIELDS,
    RATE_FIELDS,
    ComparisonAgent,
)
from src.models.loan_record import CorrectionType
from src.models.review_result import MismatchSeverity

CRITICAL = MismatchSeverity.CRITICAL
WARNING = MismatchSeverity.WARNING


@pytest.fixture
def agent():
    return ComparisonAgent()


@pytest.fixture
def full_record(make_record):
    return make_record(
        loan_amount=250000.0,
        interest_rate=3.5,
        maturity_date=date(2054, 1, 1),
    )


@pytest.mark.parametrize(
    "field_name, doc_value, is_match, severity",
    [
        ("borrower_name", "Mr. John Smith Jr.", True, None),
        ("borrower_name", "Smith John", True, None),
        ("borrower_name", "Jane Doe", False, WARNING),
        ("property_address", "123 Main St.", True, None),
        ("property_address", "999 Oak Avenue", False, WARNING),
        ("loan_amount", "$250,000.00", True, None),
        ("loan_amount", "260000", False, CRITICAL),
        ("loan_amount", "not a number", False, CRITICAL),
        ("interest_rate", "3.5%", True, None),
        ("interest_rate", "4.0%", False, CRITICAL),
        ("loan_number", "1234567890", True, None),
        ("loan_number", "0987654321", False, CRITICAL),
        ("maturity_date", "2054-01-01", True, None),
        ("maturity_date", "2055-01-01", False, CRITICAL),
    ],
)
def test_compare_routes_fields(
    agent, full_record, make_extraction, field_name, doc_value, is_match, severity
):
    comparisons = agent.compare(make_extraction({field_name: doc_value}), full_record)

    assert len(comparisons) == 1
    comparison = comparisons[0]
    assert comparison.field_name == field_name
    assert comparison.document_value == doc_value
    assert comparison.is_match is is_match
    assert comparison.mismatch_severity == severity
    assert 0.0 <= comparison.similarity_score <= 1.0
    if is_match:
        assert comparison.similarity_score > 0.8


def test_fields_without_record_value_are_skipped(agent, make_record, make_extraction):
    extraction = make_extraction(
        {
            "modification_date": "2024-01-01",
            "loan_amount": "100",
            "interest_rate": "3.5",
            "maturity_date": "2054-01-01",
            "loan_number": "1234567890",
        }
    )

    comparisons = agent.compare(extraction, make_record())

    assert [c.field_name for c in comparisons] == ["loan_number"]


def test_empty_extraction_returns_no_comparisons(agent, make_record, make_extraction):
    assert agent.compare(make_extraction({}), make_record()) == []


def test_proposed_value_overrides_record_field(agent, make_record, make_extraction):
    record = make_record(
        correction_type=CorrectionType.BORROWER_NAME,
        borrower_name="Jon Smyth",
        proposed_value="John Smith",
    )

    comparisons = agent.compare(make_extraction({"borrower_name": "John Smith"}), record)

    assert comparisons[0].record_value == "John Smith"
    assert comparisons[0].is_match is True


def test_record_to_fields_minimal(make_record):
    fields = ComparisonAgent._record_to_fields(make_record())

    assert fields == {
        "loan_number": "1234567890",
        "borrower_name": "John Smith",
        "property_address": "123 Main Street",
        "loan_type": "conventional",
    }


def test_record_to_fields_full(full_record):
    fields = ComparisonAgent._record_to_fields(full_record)

    assert fields["loan_amount"] == "250000.0"
    assert fields["interest_rate"] == "3.5"
    assert fields["maturity_date"] == "2054-01-01"


@pytest.mark.parametrize(
    "field_name, doc_value, record_value, is_match, severity",
    [
        ("new_borrower", "Jane Doe", "Jane Doe", True, None),
        ("recipient_address", "1 Elm Street", "1 Elm St", True, None),
        ("current_balance", "1,000.00", "1000", True, None),
        ("original_amount", "1000", "2000", False, WARNING),
        ("new_payment_amount", "1500", "1600", False, CRITICAL),
        ("coverage_percentage", "25%", "25", True, None),
        ("new_interest_rate", "4.25", "3.25", False, CRITICAL),
        ("certificate_number", "MI-1", "MI-2", False, WARNING),
    ],
)
def test_compare_field_routing(
    agent, field_name, doc_value, record_value, is_match, severity
):
    comparison = agent._compare_field(field_name, doc_value, record_value)

    assert comparison.is_match is is_match
    assert comparison.mismatch_severity == severity
    assert comparison.record_value == record_value


def test_field_groups_are_disjoint():
    groups = [NAME_FIELDS, ADDRESS_FIELDS, AMOUNT_FIELDS, RATE_FIELDS]
    for i, a in enumerate(groups):
        for b in groups[i + 1 :]:
            assert not a & b


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Bug: PAYMENT_AMOUNT/MI_COVERAGE proposed values are keyed as "
        "'payment_amount'/'mi_coverage', which no extractor emits, so they are never compared"
    ),
)
@pytest.mark.parametrize(
    "correction_type, field_name, value",
    [
        (CorrectionType.PAYMENT_AMOUNT, "new_payment_amount", "1500.00"),
        (CorrectionType.MI_COVERAGE, "coverage_percentage", "25"),
    ],
)
def test_proposed_value_compared_for_extracted_field(
    agent, make_record, make_extraction, correction_type, field_name, value
):
    record = make_record(correction_type=correction_type, proposed_value=value)

    comparisons = agent.compare(make_extraction({field_name: value}), record)

    assert [c.field_name for c in comparisons] == [field_name]
