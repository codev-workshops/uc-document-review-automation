"""Tests for pluggable similarity strategies and their registry."""

import pytest

from src.comparators import strategies
from src.comparators.fuzzy_comparator import FuzzyComparator, clean_name_tokens
from src.comparators.strategies import (
    JaccardAddressStrategy,
    JaccardNameStrategy,
    LevenshteinAddressStrategy,
    LevenshteinNameStrategy,
    get_address_strategy,
    get_name_strategy,
)


class TestJaccardNameStrategy:
    def setup_method(self):
        self.strategy = JaccardNameStrategy()

    def test_identical(self):
        assert self.strategy("john smith", "john smith") == 1.0

    def test_reordered(self):
        assert self.strategy("smith john", "john smith") == 1.0

    def test_partial_overlap(self):
        assert self.strategy("john smith", "john smyth") == pytest.approx(1 / 3)

    def test_disjoint(self):
        assert self.strategy("john smith", "jane doe") == 0.0

    def test_both_empty(self):
        assert self.strategy("", "") == 1.0


class TestLevenshteinNameStrategy:
    def setup_method(self):
        self.strategy = LevenshteinNameStrategy()

    def test_identical(self):
        assert self.strategy("john smith", "john smith") == 1.0

    def test_reordered_tokens_are_equal(self):
        assert self.strategy("smith john", "john smith") == 1.0

    def test_single_typo_scores_high(self):
        score = self.strategy("john smith", "jon smith")
        assert 0.85 <= score < 1.0

    def test_typo_outscores_jaccard(self):
        assert self.strategy("john smith", "jon smith") > JaccardNameStrategy()(
            "john smith", "jon smith"
        )

    def test_disjoint_scores_low(self):
        assert self.strategy("john smith", "jane doe") < 0.5

    def test_range(self):
        for a, b in [("a", "b"), ("abc", ""), ("maria garcia", "mario garcia")]:
            assert 0.0 <= self.strategy(a, b) <= 1.0


class TestJaccardAddressStrategy:
    def setup_method(self):
        self.strategy = JaccardAddressStrategy()

    def test_identical(self):
        assert self.strategy("123 main st", "123 main st") == 1.0

    def test_one_token_diff(self):
        assert self.strategy("123 main st", "124 main st") == pytest.approx(0.5)

    def test_disjoint(self):
        assert self.strategy("123 main st", "789 elm blvd") == 0.0


class TestLevenshteinAddressStrategy:
    def setup_method(self):
        self.strategy = LevenshteinAddressStrategy()

    def test_identical(self):
        assert self.strategy("123 main st", "123 main st") == 1.0

    def test_one_char_diff_scores_high(self):
        assert self.strategy("123 main st", "124 main st") > 0.9

    def test_disjoint_scores_low(self):
        assert self.strategy("123 main st", "789 elm blvd") < 0.5


class TestRegistry:
    def test_available_algorithms(self):
        assert strategies.available_algorithms() == ["jaccard", "levenshtein"]

    def test_name_lookup(self):
        assert isinstance(get_name_strategy("jaccard"), JaccardNameStrategy)
        assert isinstance(get_name_strategy("Levenshtein"), LevenshteinNameStrategy)

    def test_address_lookup(self):
        assert isinstance(get_address_strategy("jaccard"), JaccardAddressStrategy)
        assert isinstance(get_address_strategy("levenshtein"), LevenshteinAddressStrategy)

    def test_unknown_algorithm_raises(self):
        with pytest.raises(ValueError, match="Unknown name algorithm"):
            get_name_strategy("soundex")
        with pytest.raises(ValueError, match="Unknown address algorithm"):
            get_address_strategy("soundex")


class TestFuzzyComparatorInjection:
    def test_defaults_to_jaccard(self):
        comparator = FuzzyComparator()
        assert isinstance(comparator.name_strategy, JaccardNameStrategy)
        assert isinstance(comparator.address_strategy, JaccardAddressStrategy)

    def test_injected_strategy_is_used(self):
        calls: list[tuple[str, str]] = []

        def spy(a: str, b: str) -> float:
            calls.append((a, b))
            return 0.42

        comparator = FuzzyComparator(name_strategy=spy, address_strategy=spy)
        assert comparator.compare_names("Mr. John Smith", "Smith, John") == 0.42
        assert comparator.compare_addresses("1 Main Street", "2 Main St") == 0.42
        assert calls == [("john smith", "smith john"), ("1 main st", "2 main st")]

    def test_normalization_shared_across_algorithms(self):
        lev = FuzzyComparator(
            name_strategy=LevenshteinNameStrategy(),
            address_strategy=LevenshteinAddressStrategy(),
        )
        assert lev.compare_addresses("456 North Oak Avenue", "456 N Oak Ave") == 1.0
        assert lev.compare_names("Dr. Smith John Jr.", "John Smith") == 1.0

    def test_empty_handling_independent_of_strategy(self):
        lev = FuzzyComparator(name_strategy=LevenshteinNameStrategy())
        assert lev.compare_names("", "") == 1.0
        assert lev.compare_names("John", "") == 0.0
        assert lev.compare_names("Mr.", "Jr.") == 1.0


class TestNameTokenization:
    def test_ascii_baseline(self):
        assert clean_name_tokens("Mr. John Smith Jr.") == ["john", "smith"]

    def test_preserves_hyphen(self):
        assert clean_name_tokens("Jean-Luc Picard") == ["jean-luc", "picard"]

    def test_preserves_apostrophe(self):
        assert clean_name_tokens("Conor O'Brien") == ["conor", "o'brien"]

    def test_curly_apostrophe_normalized(self):
        assert clean_name_tokens("Conor O\u2019Brien") == ["conor", "o'brien"]

    def test_unicode_letters(self):
        assert clean_name_tokens("José Muñoz Gärtner") == ["josé", "muñoz", "gärtner"]

    def test_casefold_unicode(self):
        assert clean_name_tokens("JOSÉ MUÑOZ") == ["josé", "muñoz"]

    def test_non_latin_script(self):
        assert clean_name_tokens("Владимир Петров") == ["владимир", "петров"]

    def test_dangling_punctuation_dropped(self):
        assert clean_name_tokens("-John 'Smith'") == ["john", "smith"]

    def test_digits_are_not_name_tokens(self):
        assert clean_name_tokens("John Smith 3rd") == ["john", "smith", "rd"]

    def test_hyphenated_name_matches_across_algorithms(self):
        for algo in ("jaccard", "levenshtein"):
            comparator = FuzzyComparator(name_strategy=get_name_strategy(algo))
            assert comparator.compare_names("Mary-Jane O'Neil", "MARY-JANE O’NEIL") == 1.0
