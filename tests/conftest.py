"""Shared fixtures for the unit test suite."""

import socket
from datetime import datetime

import pytest

from src.models.document import (
    DocumentMetadata,
    DocumentType,
    ExtractedField,
    ExtractionResult,
    ExtractionStatus,
)
from src.models.loan_record import CorrectionType, LoanCorrectionRecord


@pytest.fixture(autouse=True)
def _block_network(monkeypatch):
    """Fail fast if any test tries to open a network connection."""

    def guard(*args, **kwargs):
        raise RuntimeError("Network access is disabled in unit tests")

    monkeypatch.setattr(socket.socket, "connect", guard)
    monkeypatch.setattr(socket, "create_connection", guard)


@pytest.fixture
def make_file(tmp_path):
    """Create a small file on disk and return its path."""

    def _make(name: str = "document.pdf", content: bytes = b"%PDF-1.4 test"):
        path = tmp_path / name
        path.write_bytes(content)
        return path

    return _make


@pytest.fixture
def make_metadata():
    def _make(
        mime_type: str = "application/pdf",
        document_type: DocumentType = DocumentType.LOAN_MODIFICATION,
        document_id: str = "doc-001",
        filename: str = "document.pdf",
    ) -> DocumentMetadata:
        return DocumentMetadata(
            document_id=document_id,
            filename=filename,
            document_type=document_type,
            upload_timestamp=datetime(2024, 1, 15, 10, 30),
            file_size_bytes=1024,
            mime_type=mime_type,
        )

    return _make


@pytest.fixture
def make_record():
    def _make(**overrides) -> LoanCorrectionRecord:
        values = dict(
            correction_id="COR-000001",
            loan_number="1234567890",
            correction_type=CorrectionType.LOAN_TYPE,
            current_value="fha",
            proposed_value="conventional",
            submitted_by="analyst-1",
            submitted_at=datetime(2024, 1, 15, 10, 30),
            borrower_name="John Smith",
            property_address="123 Main Street",
        )
        values.update(overrides)
        return LoanCorrectionRecord(**values)

    return _make


@pytest.fixture
def make_extraction():
    def _make(
        fields: dict[str, str],
        document_type: DocumentType = DocumentType.LOAN_MODIFICATION,
    ) -> ExtractionResult:
        return ExtractionResult(
            document_id="doc-001",
            document_type=document_type,
            status=ExtractionStatus.COMPLETED,
            fields=[
                ExtractedField(field_name=name, field_value=value, confidence=0.99)
                for name, value in fields.items()
            ],
        )

    return _make
