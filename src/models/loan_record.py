"""Models for loan correction records."""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


class CorrectionType(Enum):
    BORROWER_NAME = "borrower_name"
    PROPERTY_ADDRESS = "property_address"
    LOAN_AMOUNT = "loan_amount"
    INTEREST_RATE = "interest_rate"
    MATURITY_DATE = "maturity_date"
    PAYMENT_AMOUNT = "payment_amount"
    MI_COVERAGE = "mi_coverage"
    LOAN_TYPE = "loan_type"
    OCCUPANCY_STATUS = "occupancy_status"


@dataclass
class LoanCorrectionRecord:
    """A loan correction request submitted for validation."""

    correction_id: str
    loan_number: str
    correction_type: CorrectionType
    current_value: str
    proposed_value: str
    submitted_by: str
    submitted_at: datetime
    supporting_document_ids: list[str] = field(default_factory=list)
    borrower_name: str = ""
    property_address: str = ""
    loan_amount: Optional[float] = None
    interest_rate: Optional[float] = None
    maturity_date: Optional[date] = None
    notes: str = ""


@dataclass
class LoanCorrectionBatch:
    """A batch of corrections submitted together."""

    batch_id: str
    records: list[LoanCorrectionRecord] = field(default_factory=list)
    submitted_at: Optional[datetime] = None
    total_count: int = 0

    def add_record(self, record: LoanCorrectionRecord) -> None:
        self.records.append(record)
        self.total_count = len(self.records)
