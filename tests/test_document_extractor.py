"""Tests for the Document Extraction Agent."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.agents.document_extractor import MIME_EXTRACTORS, DocumentExtractionAgent
from src.extractors.pdf_extractor import DOCUMENT_FIELD_MAP
from src.models.document import (
    DocumentType,
    ExtractedField,
    ExtractionResult,
    ExtractionStatus,
)


@pytest.fixture
def agent():
    return DocumentExtractionAgent()


def test_constructor_wires_extractors(tmp_path):
    agent = DocumentExtractionAgent(
        ocr_service_url="https://ocr.test",
        ocr_api_key="secret",
        templates_dir=str(tmp_path),
    )

    assert agent.pdf_extractor.ocr_service_url == "https://ocr.test"
    assert agent.image_extractor.ocr_service_url == "https://ocr.test"
    assert agent.image_extractor.ocr_api_key == "secret"
    assert agent.form_extractor.templates_dir == tmp_path


@pytest.mark.parametrize("mime_type", ["text/plain", "application/msword", ""])
def test_unsupported_mime_type_fails(agent, make_file, make_metadata, mime_type):
    metadata = make_metadata(mime_type=mime_type, document_id="doc-xyz")
    agent.form_extractor = MagicMock()

    result = agent.extract_document(make_file(), metadata)

    assert result.status == ExtractionStatus.FAILED
    assert result.document_id == "doc-xyz"
    assert result.document_type == metadata.document_type
    assert result.error_message == f"Unsupported MIME type: {mime_type}"
    agent.form_extractor.extract.assert_not_called()


def test_pdf_falls_back_to_pdf_extractor(agent, make_file, make_metadata):
    metadata = make_metadata(
        mime_type="application/pdf", document_type=DocumentType.MI_CERTIFICATE
    )

    result = agent.extract_document(make_file("cert.pdf"), metadata)

    assert result.status == ExtractionStatus.COMPLETED
    assert [f.field_name for f in result.fields] == DOCUMENT_FIELD_MAP[
        DocumentType.MI_CERTIFICATE
    ]
    assert result.raw_text == "[Extracted text from cert.pdf]"
    assert isinstance(result.extraction_timestamp, datetime)


@pytest.mark.parametrize(
    "mime_type", [m for m, kind in MIME_EXTRACTORS.items() if kind == "image"]
)
def test_image_falls_back_to_image_extractor(agent, make_file, make_metadata, mime_type):
    metadata = make_metadata(mime_type=mime_type)

    result = agent.extract_document(make_file("scan.png"), metadata)

    assert result.status == ExtractionStatus.COMPLETED
    assert result.raw_text == "[OCR text from scan.png]"
    assert isinstance(result.extraction_timestamp, datetime)


def test_form_extraction_with_fields_short_circuits(agent, make_file, make_metadata):
    form_result = ExtractionResult(
        document_id="doc-001",
        document_type=DocumentType.LOAN_MODIFICATION,
        status=ExtractionStatus.COMPLETED,
        fields=[ExtractedField(field_name="loan_number", field_value="1", confidence=0.99)],
    )
    agent.form_extractor = MagicMock()
    agent.form_extractor.extract.return_value = form_result
    agent.pdf_extractor = MagicMock()
    agent.image_extractor = MagicMock()
    path = make_file()

    result = agent.extract_document(path, make_metadata())

    assert result is form_result
    assert isinstance(result.extraction_timestamp, datetime)
    agent.form_extractor.extract.assert_called_once_with(
        path, DocumentType.LOAN_MODIFICATION
    )
    agent.pdf_extractor.extract.assert_not_called()
    agent.image_extractor.extract.assert_not_called()


def test_form_completed_without_fields_falls_back(tmp_path, make_file, make_metadata):
    (tmp_path / "loan_modification.json").write_text("{}")
    agent = DocumentExtractionAgent(templates_dir=str(tmp_path))
    agent.pdf_extractor = MagicMock(wraps=agent.pdf_extractor)

    result = agent.extract_document(make_file(), make_metadata())

    agent.pdf_extractor.extract.assert_called_once()
    assert len(result.fields) == len(DOCUMENT_FIELD_MAP[DocumentType.LOAN_MODIFICATION])


def test_missing_file_reports_failure_with_timestamp(agent, tmp_path, make_metadata):
    result = agent.extract_document(tmp_path / "missing.pdf", make_metadata())

    assert result.status == ExtractionStatus.FAILED
    assert result.error_message.startswith("File not found")
    assert isinstance(result.extraction_timestamp, datetime)


def test_extract_batch_preserves_order(agent, make_file, make_metadata):
    documents = [
        (make_file("a.pdf"), make_metadata(mime_type="application/pdf")),
        (make_file("b.png"), make_metadata(mime_type="image/png")),
        (make_file("c.txt"), make_metadata(mime_type="text/plain", document_id="c")),
    ]

    results = agent.extract_batch(documents)

    assert [r.status for r in results] == [
        ExtractionStatus.COMPLETED,
        ExtractionStatus.COMPLETED,
        ExtractionStatus.FAILED,
    ]
    assert results[0].raw_text.endswith("a.pdf]")
    assert results[1].raw_text.endswith("b.png]")


def test_extract_batch_empty(agent):
    assert agent.extract_batch([]) == []


@pytest.mark.xfail(
    strict=True,
    reason="Bug: extractors set document_id from the file stem, not metadata.document_id",
)
def test_result_document_id_matches_metadata(agent, make_file, make_metadata):
    metadata = make_metadata(document_id="doc-123")

    result = agent.extract_document(make_file("upload_9f3a.pdf"), metadata)

    assert result.document_id == "doc-123"
