"""Date comparison with support for common document formats."""

from datetime import date, datetime
from typing import Iterable, Optional

from src.comparators.amount_comparator import ComparisonStatus, NumericComparison

DATE_FORMATS = (
    "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%b %d, %Y",
    "%B %d, %Y", "%d %b %Y", "%d %B %Y", "%Y%m%d", "%Y/%m/%d",
)


class DateComparator:
    """Compares dates across common document formats."""

    def __init__(self, formats: Iterable[str] = DATE_FORMATS):
        self.formats = tuple(formats)

    @staticmethod
    def parse_date(
        value: str,
        formats: Iterable[str] = DATE_FORMATS,
    ) -> Optional[date]:
        """Parse a date using the supplied formats."""
        if not value or not value.strip():
            return None
        for fmt in formats:
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def compare(self, a: str, b: str) -> NumericComparison:
        parsed_a = self.parse_date(a, self.formats)
        parsed_b = self.parse_date(b, self.formats)
        if parsed_a is None or parsed_b is None:
            return NumericComparison(False, 0.0, ComparisonStatus.UNPARSEABLE)
        if parsed_a == parsed_b:
            return NumericComparison(True, 1.0, ComparisonStatus.MATCH)
        return NumericComparison(False, 0.0, ComparisonStatus.MISMATCH)
