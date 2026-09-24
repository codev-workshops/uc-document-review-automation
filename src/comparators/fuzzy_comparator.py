"""Fuzzy matching for name and address fields.

Normalization (noise stripping, abbreviation handling) is a fixed, shared
pre-step; the final scoring is delegated to an injected
``SimilarityStrategy`` so the algorithm can be swapped via configuration.
"""

import logging
import re
from typing import Optional

from src.comparators.strategies import (
    JaccardAddressStrategy,
    JaccardNameStrategy,
    SimilarityStrategy,
)

logger = logging.getLogger(__name__)

# Common address abbreviation mappings
ADDRESS_ABBREVIATIONS: dict[str, str] = {
    "street": "st",
    "avenue": "ave",
    "boulevard": "blvd",
    "drive": "dr",
    "lane": "ln",
    "road": "rd",
    "court": "ct",
    "place": "pl",
    "circle": "cir",
    "apartment": "apt",
    "suite": "ste",
    "building": "bldg",
    "north": "n",
    "south": "s",
    "east": "e",
    "west": "w",
}

# Common name prefixes/suffixes to strip
NAME_NOISE = {"mr", "mrs", "ms", "dr", "jr", "sr", "ii", "iii", "iv"}

# Unicode letters, optionally joined by a single hyphen or apostrophe
# (e.g. "o'brien", "jean-luc", "muñoz").
_NAME_TOKEN_RE = re.compile(r"[^\W\d_]+(?:['\-][^\W\d_]+)*")
_APOSTROPHE_VARIANTS_RE = re.compile("[\u2018\u2019\u02bc\u0060\u00b4]")
_HYPHEN_VARIANTS_RE = re.compile("[\u2010\u2011\u2012\u2013\u2014]")


def clean_name_tokens(name: str) -> list[str]:
    """Tokenize a name, removing noise words and normalizing case/punctuation."""
    text = _APOSTROPHE_VARIANTS_RE.sub("'", name)
    text = _HYPHEN_VARIANTS_RE.sub("-", text).casefold()
    tokens = _NAME_TOKEN_RE.findall(text)
    return [t for t in tokens if t not in NAME_NOISE]


def normalize_name(name: str) -> str:
    """Canonical whitespace-joined form of ``clean_name_tokens``."""
    return " ".join(clean_name_tokens(name))


def normalize_address(address: str) -> str:
    """Normalize an address by collapsing abbreviations and punctuation."""
    addr = address.lower().strip()
    addr = re.sub(r"[.,#]", " ", addr)
    addr = " ".join(addr.split())

    for full, abbr in ADDRESS_ABBREVIATIONS.items():
        addr = re.sub(rf"\b{full}\b", abbr, addr)
        addr = re.sub(rf"\b{abbr}\.\b", abbr, addr)

    return addr


class FuzzyComparator:
    """Specialized fuzzy matching for names and addresses."""

    def __init__(
        self,
        name_strategy: Optional[SimilarityStrategy] = None,
        address_strategy: Optional[SimilarityStrategy] = None,
    ) -> None:
        self.name_strategy: SimilarityStrategy = name_strategy or JaccardNameStrategy()
        self.address_strategy: SimilarityStrategy = (
            address_strategy or JaccardAddressStrategy()
        )

    def compare_names(self, name_a: str, name_b: str) -> float:
        """Compare two person names with tolerance for ordering and prefixes."""
        norm_a = normalize_name(name_a)
        norm_b = normalize_name(name_b)

        if not norm_a and not norm_b:
            return 1.0
        if not norm_a or not norm_b:
            return 0.0

        return self.name_strategy(norm_a, norm_b)

    def compare_addresses(self, addr_a: str, addr_b: str) -> float:
        """Compare two addresses with abbreviation normalization."""
        norm_a = normalize_address(addr_a)
        norm_b = normalize_address(addr_b)

        if norm_a == norm_b:
            return 1.0
        if not norm_a or not norm_b:
            return 0.0

        return self.address_strategy(norm_a, norm_b)

    @staticmethod
    def _clean_name_tokens(name: str) -> list[str]:
        return clean_name_tokens(name)

    @staticmethod
    def _normalize_address(address: str) -> str:
        return normalize_address(address)
