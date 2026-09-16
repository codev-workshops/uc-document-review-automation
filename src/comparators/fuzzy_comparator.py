"""Fuzzy matching for name and address fields."""

import logging
import re
from typing import Callable, Iterable, Optional

logger = logging.getLogger(__name__)

ADDRESS_ABBREVIATIONS: dict[str, str] = {
    "street": "st", "avenue": "ave", "boulevard": "blvd", "drive": "dr",
    "lane": "ln", "road": "rd", "court": "ct", "place": "pl",
    "circle": "cir", "apartment": "apt", "suite": "ste", "building": "bldg",
    "north": "n", "south": "s", "east": "e", "west": "w",
}
NAME_NOISE = {"mr", "mrs", "ms", "dr", "jr", "sr", "ii", "iii", "iv"}


class UnknownAlgorithmError(ValueError):
    """Raised when a fuzzy similarity algorithm is not supported."""


TokenSimilarity = Callable[[list[str], list[str]], float]


def jaccard_similarity(a: list[str], b: list[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    union = set(a) | set(b)
    return len(set(a) & set(b)) / len(union) if union else 0.0


def levenshtein_ratio(s: str, t: str) -> float:
    if not s and not t:
        return 1.0
    if not s or not t:
        return 0.0
    previous = list(range(len(t) + 1))
    for i, char_s in enumerate(s, 1):
        current = [i]
        for j, char_t in enumerate(t, 1):
            current.append(min(
                current[-1] + 1,
                previous[j] + 1,
                previous[j - 1] + (char_s != char_t),
            ))
        previous = current
    return 1.0 - previous[-1] / max(len(s), len(t))


def levenshtein_similarity(a: list[str], b: list[str]) -> float:
    return levenshtein_ratio(" ".join(a), " ".join(b))


def hybrid_similarity(a: list[str], b: list[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    sum_a = sum(max(levenshtein_ratio(token, other) for other in b) for token in a)
    sum_b = sum(max(levenshtein_ratio(token, other) for other in a) for token in b)
    return (sum_a + sum_b) / (len(a) + len(b))


SIMILARITY_ALGORITHMS: dict[str, TokenSimilarity] = {
    "jaccard": jaccard_similarity,
    "levenshtein": levenshtein_similarity,
    "hybrid": hybrid_similarity,
}


class FuzzyComparator:
    """Specialized fuzzy matching for names and addresses."""

    def __init__(
        self,
        algorithm: str = "jaccard",
        name_threshold: float = 0.85,
        address_threshold: float = 0.80,
        name_noise: Optional[Iterable[str]] = None,
        address_abbreviations: Optional[dict[str, str]] = None,
    ) -> None:
        if algorithm not in SIMILARITY_ALGORITHMS:
            raise UnknownAlgorithmError(
                f"Unknown fuzzy algorithm '{algorithm}'; expected one of "
                f"{sorted(SIMILARITY_ALGORITHMS)}"
            )
        self.algorithm = algorithm
        self.similarity = SIMILARITY_ALGORITHMS[algorithm]
        self.name_threshold = name_threshold
        self.address_threshold = address_threshold
        self.name_noise = frozenset(NAME_NOISE if name_noise is None else name_noise)
        self.address_abbreviations = dict(
            ADDRESS_ABBREVIATIONS if address_abbreviations is None else address_abbreviations
        )

    def compare_names(self, name_a: str, name_b: str) -> float:
        return self.similarity(
            self._clean_name_tokens(name_a), self._clean_name_tokens(name_b)
        )

    def compare_addresses(self, addr_a: str, addr_b: str) -> float:
        norm_a = self._normalize_address(addr_a)
        norm_b = self._normalize_address(addr_b)
        if norm_a == norm_b:
            return 1.0
        return self.similarity(norm_a.split(), norm_b.split())

    def compare_text(self, a: str, b: str) -> float:
        return self.similarity(a.lower().split(), b.lower().split())

    def _clean_name_tokens(self, name: str) -> list[str]:
        tokens = re.findall(r"[a-z]+", name.lower())
        return [token for token in tokens if token not in self.name_noise]

    def _normalize_address(self, address: str) -> str:
        addr = address.lower().strip()
        addr = re.sub(r"[.,#]", " ", addr)
        addr = " ".join(addr.split())
        for full, abbr in self.address_abbreviations.items():
            addr = re.sub(rf"\b{full}\b", abbr, addr)
            addr = re.sub(rf"\b{abbr}\.\b", abbr, addr)
        return addr
