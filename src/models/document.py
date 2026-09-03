"""Models for document metadata, content, and extraction results."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class DocumentType(Enum):
    LOAN_MODIFICATION = "loan_modification"
    MI_CERTIFICATE = "mi_certificate"
    COPY_OF_NOTE = "copy_of_note"
    ASSUMPTION_AGREEMENT = "assumption_agreement"
    USPS_DOCUMENT = "usps_document"
    LOAN_HISTORY = "loan_history"
    OTHER = "other"


class ExtractionStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DocumentMetadata:
    """Metadata about an uploaded document."""

    document_id: str
    filename: str
    document_type: DocumentType
    upload_timestamp: datetime
    file_size_bytes: int
    mime_type: str
    page_count: int = 1
    source_system: str = ""


@dataclass
class ExtractedField:
    """A single field extracted from a document."""

    field_name: str
    field_value: str
    confidence: float
    page_number: int = 1
    bounding_box: Optional[list[float]] = None

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.90


@dataclass
class ExtractionResult:
    """The full extraction result for a single document."""

    document_id: str
    document_type: DocumentType
    status: ExtractionStatus
    fields: list[ExtractedField] = field(default_factory=list)
    raw_text: str = ""
    extraction_timestamp: Optional[datetime] = None
    error_message: Optional[str] = None

    @property
    def low_confidence_fields(self) -> list[ExtractedField]:
        return [f for f in self.fields if not f.is_high_confidence]

    def get_field(self, name: str) -> Optional[ExtractedField]:
        for f in self.fields:
            if f.field_name == name:
                return f
        return None
