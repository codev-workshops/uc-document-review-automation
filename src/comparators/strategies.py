"""Pluggable similarity strategies for fuzzy name/address matching.

A strategy scores two *already-normalized* strings (see
``fuzzy_comparator.normalize_name`` / ``normalize_address``) and returns a
float in ``[0.0, 1.0]``. Normalization is deliberately kept outside the
strategy so every algorithm benefits from the same noise stripping and
address-abbreviation handling.
"""

from __future__ import annotations

from typing import Protocol

from rapidfuzz.distance import Levenshtein


class SimilarityStrategy(Protocol):
    """Callable scoring two normalized strings -> similarity in [0, 1]."""

    def __call__(self, normalized_a: str, normalized_b: str) -> float: ...


def _token_set_jaccard(a: str, b: str) -> float:
    set_a = set(a.split())
    set_b = set(b.split())
    union = set_a | set_b
    if not union:
        return 1.0 if a == b else 0.0
    return len(set_a & set_b) / len(union)


def _sorted_tokens(value: str) -> str:
    return " ".join(sorted(value.split()))


class JaccardNameStrategy:
    """Token-set Jaccard over name tokens (order-insensitive)."""

    def __call__(self, normalized_a: str, normalized_b: str) -> float:
        return _token_set_jaccard(normalized_a, normalized_b)


class JaccardAddressStrategy:
    """Token-set Jaccard over normalized address tokens."""

    def __call__(self, normalized_a: str, normalized_b: str) -> float:
        if normalized_a == normalized_b:
            return 1.0
        return _token_set_jaccard(normalized_a, normalized_b)


class LevenshteinNameStrategy:
    """Normalized Levenshtein similarity over token-sorted names.

    Sorting tokens first keeps the order-insensitivity of the Jaccard
    approach ("Smith John" == "John Smith") while tolerating small spelling
    differences ("Jon" vs "John") that Jaccard scores as total token misses.
    """

    def __call__(self, normalized_a: str, normalized_b: str) -> float:
        return Levenshtein.normalized_similarity(
            _sorted_tokens(normalized_a), _sorted_tokens(normalized_b)
        )


class LevenshteinAddressStrategy:
    """Normalized Levenshtein similarity over normalized address strings."""

    def __call__(self, normalized_a: str, normalized_b: str) -> float:
        if normalized_a == normalized_b:
            return 1.0
        return Levenshtein.normalized_similarity(normalized_a, normalized_b)


JACCARD = "jaccard"
LEVENSHTEIN = "levenshtein"

NAME_STRATEGIES: dict[str, type[SimilarityStrategy]] = {
    JACCARD: JaccardNameStrategy,
    LEVENSHTEIN: LevenshteinNameStrategy,
}

ADDRESS_STRATEGIES: dict[str, type[SimilarityStrategy]] = {
    JACCARD: JaccardAddressStrategy,
    LEVENSHTEIN: LevenshteinAddressStrategy,
}


def available_algorithms() -> list[str]:
    return sorted(NAME_STRATEGIES)


def _lookup(
    registry: dict[str, type[SimilarityStrategy]], kind: str, algorithm: str
) -> SimilarityStrategy:
    key = algorithm.strip().lower()
    try:
        return registry[key]()
    except KeyError:
        raise ValueError(
            f"Unknown {kind} algorithm {algorithm!r}; expected one of {sorted(registry)}"
        ) from None


def get_name_strategy(algorithm: str) -> SimilarityStrategy:
    return _lookup(NAME_STRATEGIES, "name", algorithm)


def get_address_strategy(algorithm: str) -> SimilarityStrategy:
    return _lookup(ADDRESS_STRATEGIES, "address", algorithm)
