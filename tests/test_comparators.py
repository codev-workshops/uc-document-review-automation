"""Tests for field, fuzzy, and amount comparators."""

import pytest

from src.comparators.amount_comparator import AmountComparator, ComparisonStatus
from src.comparators.date_comparator import DateComparator
from src.comparators.field_comparator import FieldComparator
from src.comparators.fuzzy_comparator import FuzzyComparator
from src.models.review_result import MismatchSeverity


class TestFieldComparator:
    def setup_method(self):
        self.comparator = FieldComparator()

    def test_exact_match_field_matches(self):
        result = self.comparator.compare("loan_number", "12345", "12345")
        assert result.is_match is True
        assert result.similarity_score == 1.0
        assert result.mismatch_severity is None

    def test_exact_match_field_case_insensitive(self):
        result = self.comparator.compare("loan_number", "ABC123", "abc123")
        assert result.is_match is True

    def test_exact_match_field_mismatch_is_critical(self):
        result = self.comparator.compare("loan_number", "12345", "67890")
        assert result.is_match is False
        assert result.similarity_score == 0.0
        assert result.mismatch_severity == MismatchSeverity.CRITICAL

    def test_tolerant_field_close_match(self):
        result = self.comparator.compare("borrower_name", "John Smith", "john smith")
        assert result.is_match is True
        assert result.similarity_score >= 0.85

    def test_tolerant_field_mismatch_is_warning(self):
        result = self.comparator.compare("borrower_name", "John Smith", "Jane Doe")
        assert result.is_match is False
        assert result.mismatch_severity == MismatchSeverity.WARNING

    def test_critical_field_mismatch_severity(self):
        result = self.comparator.compare("interest_rate", "3.5", "4.0")
        assert result.is_match is False
        assert result.mismatch_severity == MismatchSeverity.CRITICAL

    def test_generic_field_exact_match(self):
        result = self.comparator.compare("occupancy_status", "primary", "primary")
        assert result.is_match is True
        assert result.similarity_score == 1.0

    def test_normalize_strips_whitespace(self):
        result = self.comparator.compare("loan_number", "  12345  ", "12345")
        assert result.is_match is True

    def test_fuzzy_similarity_identical(self):
        score = FieldComparator._fuzzy_similarity("hello world", "hello world")
        assert score == 1.0

    def test_fuzzy_similarity_empty_strings(self):
        assert FieldComparator._fuzzy_similarity("", "") == 1.0

    def test_fuzzy_similarity_one_empty(self):
        assert FieldComparator._fuzzy_similarity("hello", "") == 0.0


class TestFuzzyComparator:
    def setup_method(self):
        self.comparator = FuzzyComparator()

    def test_name_exact_match(self):
        score = self.comparator.compare_names("John Smith", "John Smith")
        assert score == 1.0

    def test_name_case_insensitive(self):
        score = self.comparator.compare_names("JOHN SMITH", "john smith")
        assert score == 1.0

    def test_name_strips_prefixes(self):
        score = self.comparator.compare_names("Mr. John Smith", "John Smith")
        assert score == 1.0

    def test_name_reordered_tokens(self):
        score = self.comparator.compare_names("Smith John", "John Smith")
        assert score == 1.0

    def test_name_completely_different(self):
        score = self.comparator.compare_names("John Smith", "Jane Doe")
        assert score < 0.5

    def test_name_empty_both(self):
        assert self.comparator.compare_names("", "") == 1.0

    def test_name_one_empty(self):
        assert self.comparator.compare_names("John", "") == 0.0

    def test_address_exact_match(self):
        score = self.comparator.compare_addresses(
            "123 Main Street", "123 Main Street"
        )
        assert score == 1.0

    def test_address_abbreviation_normalization(self):
        score = self.comparator.compare_addresses(
            "123 Main Street", "123 Main St"
        )
        assert score == 1.0

    def test_address_case_insensitive(self):
        score = self.comparator.compare_addresses(
            "123 MAIN ST", "123 main st"
        )
        assert score == 1.0

    def test_address_direction_abbreviations(self):
        score = self.comparator.compare_addresses(
            "456 North Oak Avenue", "456 N Oak Ave"
        )
        assert score == 1.0

    def test_address_completely_different(self):
        score = self.comparator.compare_addresses(
            "123 Main St", "789 Elm Blvd"
        )
        assert score < 0.5


class TestAmountComparator:
    def setup_method(self):
        self.comparator = AmountComparator(tolerance=0.01)

    def test_amounts_exact_match(self):
        is_match, score = self.comparator.compare_amounts("250000.00", "250000.00")
        assert is_match is True
        assert score == 1.0

    def test_amounts_within_tolerance(self):
        is_match, score = self.comparator.compare_amounts("250000.00", "250000.005")
        assert is_match is True
        assert score == 1.0

    def test_amounts_outside_tolerance(self):
        is_match, score = self.comparator.compare_amounts("250000.00", "250100.00")
        assert is_match is False
        assert score < 1.0

    def test_amounts_with_currency_symbols(self):
        is_match, score = self.comparator.compare_amounts("$250,000.00", "250000.00")
        assert is_match is True

    def test_amounts_both_zero(self):
        is_match, score = self.comparator.compare_amounts("0", "0")
        assert is_match is True
        assert score == 1.0

    def test_amounts_unparseable(self):
        is_match, score = self.comparator.compare_amounts("N/A", "250000")
        assert is_match is False
        assert score == 0.0

    def test_amounts_empty_string(self):
        is_match, score = self.comparator.compare_amounts("", "250000")
        assert is_match is False
        assert score == 0.0

    def test_rates_exact_match(self):
        is_match, score = self.comparator.compare_rates("3.500%", "3.500")
        assert is_match is True
        assert score == 1.0

    def test_rates_mismatch(self):
        is_match, score = self.comparator.compare_rates("3.500", "4.000")
        assert is_match is False
        assert score < 1.0

    def test_rates_within_precision(self):
        is_match, score = self.comparator.compare_rates("3.5000", "3.5005")
        assert is_match is True

    def test_rates_unparseable(self):
        is_match, score = self.comparator.compare_rates("abc", "3.5")
        assert is_match is False
        assert score == 0.0


class TestFuzzyAlgorithms:
    def test_levenshtein_handles_name_typo(self):
        assert FuzzyComparator("levenshtein").compare_text(
            "John Smith", "Jon Smith"
        ) > 0.85

    def test_hybrid_handles_transposed_token(self):
        assert FuzzyComparator("hybrid").compare_names(
            "John Smtih Smith", "John Smith Doe"
        ) > 0.8

    def test_jaccard_scores_transposed_token(self):
        assert FuzzyComparator().compare_names(
            "John Smtih Smith", "John Smith Doe"
        ) == 0.5

    def test_default_jaccard_strips_name_noise(self):
        assert FuzzyComparator().compare_names(
            "Mr. John Smith", "John Smith"
        ) == 1.0

    def test_custom_name_noise_override(self):
        assert FuzzyComparator(name_noise={"esq"}).compare_names(
            "John Smith Esq", "John Smith"
        ) == 1.0

    def test_custom_address_abbreviations_override(self):
        assert FuzzyComparator(
            address_abbreviations={"highway": "hwy"}
        ).compare_addresses("1 Main Highway", "1 Main Hwy") == 1.0


class TestAmountComparatorDetailed:
    def setup_method(self):
        self.comparator = AmountComparator()

    def test_amount_mismatch_is_capped_below_match(self):
        result = self.comparator.compare_amounts_detailed(
            "$500,000.00", "$500,000.50"
        )
        assert result.is_match is False
        assert result.similarity < 1.0
        assert result.status is ComparisonStatus.MISMATCH

    def test_relative_tolerance_matches_amount(self):
        result = AmountComparator(relative_tolerance=0.001).compare_amounts_detailed(
            "500000", "500000.50"
        )
        assert result.is_match is True

    def test_unparseable_amount_status(self):
        result = self.comparator.compare_amounts_detailed("N/A", "1")
        assert result.status is ComparisonStatus.UNPARSEABLE
        assert result.parse_failed


class TestRateNormalization:
    @pytest.mark.parametrize(
        ("left", "right"),
        [("3.5%", "3.5"), ("3.5", "0.035"), ("25", "0.25")],
    )
    def test_equivalent_rate_units_match(self, left, right):
        assert AmountComparator().compare_rates(left, right)[0]

    def test_rate_mismatch_similarity_is_below_one(self):
        assert AmountComparator().compare_rates("3.5", "4.0")[1] < 1.0


class TestDateComparator:
    @pytest.mark.parametrize(
        "value",
        ["2030-01-01", "Jan 1, 2030", "January 1, 2030"],
    )
    def test_equivalent_date_formats_match(self, value):
        assert DateComparator().compare("01/01/2030", value).is_match

    def test_date_mismatch(self):
        result = DateComparator().compare("01/01/2030", "2031-01-01")
        assert result.status is ComparisonStatus.MISMATCH
        assert not result.is_match

    def test_unparseable_date(self):
        result = DateComparator().compare("someday", "01/01/2030")
        assert result.status is ComparisonStatus.UNPARSEABLE
