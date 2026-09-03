"""Tests for field, fuzzy, and amount comparators."""

from src.comparators.amount_comparator import AmountComparator
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
