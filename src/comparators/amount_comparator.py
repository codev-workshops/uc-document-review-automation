"""Numeric and currency amount comparison."""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class AmountComparator:
    """Compares monetary amounts and numeric values with tolerance."""

    def __init__(self, tolerance: float = 0.01) -> None:
        self.tolerance = tolerance

    def compare_amounts(
        self,
        amount_a: str,
        amount_b: str,
    ) -> tuple[bool, float]:
        """Compare two monetary amounts.

        Returns (is_match, similarity_score).
        """
        parsed_a = self._parse_amount(amount_a)
        parsed_b = self._parse_amount(amount_b)

        if parsed_a is None or parsed_b is None:
            return False, 0.0

        if parsed_a == 0.0 and parsed_b == 0.0:
            return True, 1.0

        diff = abs(parsed_a - parsed_b)
        max_val = max(abs(parsed_a), abs(parsed_b))

        if diff <= self.tolerance:
            return True, 1.0

        relative_diff = diff / max_val if max_val > 0 else 1.0
        similarity = max(0.0, 1.0 - relative_diff)

        return diff <= self.tolerance, similarity

    def compare_rates(
        self,
        rate_a: str,
        rate_b: str,
    ) -> tuple[bool, float]:
        """Compare two interest rates or percentages."""
        parsed_a = self._parse_rate(rate_a)
        parsed_b = self._parse_rate(rate_b)

        if parsed_a is None or parsed_b is None:
            return False, 0.0

        diff = abs(parsed_a - parsed_b)
        # Rates must match within 0.001 (e.g., 3.500% vs 3.500%)
        is_match = diff <= 0.001
        similarity = 1.0 if is_match else max(0.0, 1.0 - diff)

        return is_match, similarity

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
        cleaned = re.sub(r"[%\s]", "", value.strip())
        try:
            return float(cleaned)
        except ValueError:
            logger.debug("Could not parse rate: %s", value)
            return None
