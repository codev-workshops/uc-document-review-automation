"""Date comparison with support for common document formats."""

from datetime import date, datetime
from typing import Iterable, Optional

from src.comparators.amount_comparator import ComparisonStatus, NumericComparison

DATE_FORMATS = (
    "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%b %d, %Y",
    "%B %d, %Y", "%d %b %Y", "%d %B %Y", "%Y%m%d", "%Y/%m/%d",
)


class DateComparator:
    def __init__(self, formats: Iterable[str] = DATE_FORMATS):
        self.formats = tuple(formats)

    @staticmethod
    def parse_date(value: str) -> Optional[date]:
        if not value or not value.strip():
            return None
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def compare(self, a: str, b: str) -> NumericComparison:
        parsed_a = self._parse_with_formats(a)
        parsed_b = self._parse_with_formats(b)
        if parsed_a is None or parsed_b is None:
            return NumericComparison(False, 0.0, ComparisonStatus.UNPARSEABLE)
        if parsed_a == parsed_b:
            return NumericComparison(True, 1.0, ComparisonStatus.MATCH)
        return NumericComparison(False, 0.0, ComparisonStatus.MISMATCH)

    def _parse_with_formats(self, value: str) -> Optional[date]:
        if not value or not value.strip():
            return None
        for fmt in self.formats:
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
        return None
