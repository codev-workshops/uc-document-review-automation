"""Numeric and currency amount comparison."""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ComparisonStatus(Enum):
    MATCH = "match"
    MISMATCH = "mismatch"
    UNPARSEABLE = "unparseable"


@dataclass(frozen=True)
class NumericComparison:
    is_match: bool
    similarity: float
    status: ComparisonStatus

    @property
    def parse_failed(self) -> bool:
        return self.status is ComparisonStatus.UNPARSEABLE


MISMATCH_SIMILARITY_CAP = 0.9


class AmountComparator:
    """Compares monetary amounts and numeric values with tolerance."""

    def __init__(
        self,
        tolerance: float = 0.01,
        relative_tolerance: float = 0.0,
        rate_tolerance: float = 0.001,
    ) -> None:
        self.tolerance = tolerance
        self.relative_tolerance = relative_tolerance
        self.rate_tolerance = rate_tolerance

    def compare_amounts_detailed(self, amount_a: str, amount_b: str) -> NumericComparison:
        """Compare amounts and return match status, similarity, and parse status."""
        parsed_a = self._parse_amount(amount_a)
        parsed_b = self._parse_amount(amount_b)
        if parsed_a is None or parsed_b is None:
            return NumericComparison(False, 0.0, ComparisonStatus.UNPARSEABLE)
        if parsed_a == 0.0 and parsed_b == 0.0:
            return NumericComparison(True, 1.0, ComparisonStatus.MATCH)
        diff = abs(parsed_a - parsed_b)
        max_val = max(abs(parsed_a), abs(parsed_b))
        effective_tol = max(self.tolerance, self.relative_tolerance * max_val)
        if diff <= effective_tol:
            return NumericComparison(True, 1.0, ComparisonStatus.MATCH)
        similarity = min(
            MISMATCH_SIMILARITY_CAP,
            max(0.0, 1.0 - diff / max_val) if max_val else 0.0,
        )
        return NumericComparison(False, similarity, ComparisonStatus.MISMATCH)

    def compare_rates_detailed(self, rate_a: str, rate_b: str) -> NumericComparison:
        """Compare rates and return match status, similarity, and parse status."""
        parsed_a = self._parse_rate(rate_a)
        parsed_b = self._parse_rate(rate_b)
        if parsed_a is None or parsed_b is None:
            return NumericComparison(False, 0.0, ComparisonStatus.UNPARSEABLE)
        if parsed_a == 0.0 and parsed_b == 0.0:
            return NumericComparison(True, 1.0, ComparisonStatus.MATCH)
        diff = abs(parsed_a - parsed_b)
        if diff <= self.rate_tolerance:
            return NumericComparison(True, 1.0, ComparisonStatus.MATCH)
        max_val = max(abs(parsed_a), abs(parsed_b))
        similarity = min(
            MISMATCH_SIMILARITY_CAP,
            max(0.0, 1.0 - diff / max_val) if max_val else 0.0,
        )
        return NumericComparison(False, similarity, ComparisonStatus.MISMATCH)

    def compare_amounts(self, amount_a: str, amount_b: str) -> tuple[bool, float]:
        """Compare two monetary amounts."""
        result = self.compare_amounts_detailed(amount_a, amount_b)
        return result.is_match, result.similarity

    def compare_rates(self, rate_a: str, rate_b: str) -> tuple[bool, float]:
        """Compare two interest rates or percentages."""
        result = self.compare_rates_detailed(rate_a, rate_b)
        return result.is_match, result.similarity

    @staticmethod
    def _parse_amount(value: str) -> Optional[float]:
        """Parse a monetary string into a float."""
        if not value:
            return None
        cleaned = re.sub(r"[,$\s]", "", value.strip())
        try:
            return float(cleaned)
        except ValueError:
            logger.debug("Could not parse amount: %s", value)
            return None

    @staticmethod
    def _parse_rate(value: str) -> Optional[float]:
        """Parse a rate/percentage string into a float."""
        if not value:
            return None
        stripped = value.strip()
        has_percent = "%" in stripped
        cleaned = stripped.replace("%", "").strip()
        try:
            parsed = float(cleaned)
        except ValueError:
            logger.debug("Could not parse rate: %s", value)
            return None
        if not has_percent and 0 < abs(parsed) < 1:
            return parsed * 100
        return parsed
