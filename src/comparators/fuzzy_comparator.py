"""Fuzzy matching for name and address fields."""

import logging
import re
from typing import Optional

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


class FuzzyComparator:
    """Specialized fuzzy matching for names and addresses."""

    def compare_names(self, name_a: str, name_b: str) -> float:
        """Compare two person names with tolerance for ordering and prefixes."""
        tokens_a = self._clean_name_tokens(name_a)
        tokens_b = self._clean_name_tokens(name_b)

        if not tokens_a and not tokens_b:
            return 1.0
        if not tokens_a or not tokens_b:
            return 0.0

        # Check if all tokens from one name appear in the other
        set_a = set(tokens_a)
        set_b = set(tokens_b)
        intersection = set_a & set_b
        union = set_a | set_b

        return len(intersection) / len(union) if union else 0.0

    def compare_addresses(self, addr_a: str, addr_b: str) -> float:
        """Compare two addresses with abbreviation normalization."""
        norm_a = self._normalize_address(addr_a)
        norm_b = self._normalize_address(addr_b)

        if norm_a == norm_b:
            return 1.0

        tokens_a = set(norm_a.split())
        tokens_b = set(norm_b.split())
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b

        return len(intersection) / len(union) if union else 0.0

    @staticmethod
    def _clean_name_tokens(name: str) -> list[str]:
        """Tokenize a name, removing noise words and normalizing."""
        tokens = re.findall(r"[a-z]+", name.lower())
        return [t for t in tokens if t not in NAME_NOISE]

    @staticmethod
    def _normalize_address(address: str) -> str:
        """Normalize an address by expanding/collapsing abbreviations."""
        addr = address.lower().strip()
        # Remove punctuation
        addr = re.sub(r"[.,#]", " ", addr)
        addr = " ".join(addr.split())

        # Expand abbreviations to canonical short form
        for full, abbr in ADDRESS_ABBREVIATIONS.items():
            addr = re.sub(rf"\b{full}\b", abbr, addr)
            # Also collapse the abbreviated form
            addr = re.sub(rf"\b{abbr}\.\b", abbr, addr)

        return addr
