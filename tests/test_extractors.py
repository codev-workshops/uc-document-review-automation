"""Tests for the PDF, image (OCR) and form extractors."""

import logging
from pathlib import Path

import pytest

from src.extractors.form_extractor import FormExtractor
from src.extractors.image_extractor import ImageExtractor
from src.extractors.pdf_extractor import DOCUMENT_FIELD_MAP, PDFExtractor
from src.models.document import DocumentType, ExtractionStatus

EXTRACTOR_FACTORIES = {
    "pdf": lambda tmp_path: PDFExtractor(),
    "image": lambda tmp_path: ImageExtractor(),
    "form": lambda tmp_path: FormExtractor(templates_dir=str(tmp_path)),
}


@pytest.mark.parametrize("kind", sorted(EXTRACTOR_FACTORIES))
def test_missing_file_fails(kind, tmp_path):
    extractor = EXTRACTOR_FACTORIES[kind](tmp_path)
    missing = tmp_path / "missing.pdf"

    result = extractor.extract(missing, DocumentType.LOAN_MODIFICATION)

    assert result.status == ExtractionStatus.FAILED
    assert result.document_id == "missing"
    assert result.document_type == DocumentType.LOAN_MODIFICATION
    assert result.error_message == f"File not found: {missing}"
    assert result.fields == []


class TestPDFExtractor:
    def test_init_stores_ocr_url(self):
        assert PDFExtractor().ocr_service_url is None
        assert PDFExtractor(ocr_service_url="https://ocr.test").ocr_service_url == (
            "https://ocr.test"
        )

    @pytest.mark.parametrize(
        "document_type", list(DOCUMENT_FIELD_MAP), ids=lambda t: t.value
    )
    def test_extracts_expected_fields_per_type(self, document_type, make_file):
        path = make_file("loan_doc.pdf")

        result = PDFExtractor().extract(path, document_type)

        assert result.status == ExtractionStatus.COMPLETED
        assert result.document_id == "loan_doc"
        assert result.raw_text == "[Extracted text from loan_doc.pdf]"
        assert [f.field_name for f in result.fields] == DOCUMENT_FIELD_MAP[document_type]
        for field in result.fields:
            assert field.field_value == ""
            assert field.confidence == 0.0
            assert field.page_number == 1

    def test_unmapped_document_type_yields_no_fields(self, make_file):
        result = PDFExtractor().extract(make_file(), DocumentType.OTHER)

        assert result.status == ExtractionStatus.COMPLETED
        assert result.fields == []

    def test_raw_text_failure_returns_empty_string(self, caplog):
        class UnreadablePath:
            @property
            def name(self):
                raise OSError("disk error")

        with caplog.at_level(logging.ERROR, logger="src.extractors.pdf_extractor"):
            assert PDFExtractor()._extract_raw_text(UnreadablePath()) == ""

        assert "Text extraction failed" in caplog.text

    def test_parse_fields_empty_expected(self):
        assert PDFExtractor._parse_fields("some text", []) == []


class TestImageExtractor:
    def test_init_stores_credentials(self):
        extractor = ImageExtractor(ocr_service_url="https://ocr.test", ocr_api_key="k")
        assert extractor.ocr_service_url == "https://ocr.test"
        assert extractor.ocr_api_key == "k"

    @pytest.mark.parametrize("filename", ["scan.png", "scan.jpg", "scan.tiff"])
    def test_successful_ocr(self, filename, make_file):
        path = make_file(filename, b"\x89PNG")

        result = ImageExtractor().extract(path, DocumentType.MI_CERTIFICATE)

        assert result.status == ExtractionStatus.COMPLETED
        assert result.document_id == "scan"
        assert result.raw_text == f"[OCR text from {filename}]"
        assert result.fields == []
        assert result.error_message is None

    def test_empty_ocr_text_fails(self, make_file, monkeypatch):
        extractor = ImageExtractor()
        monkeypatch.setattr(extractor, "_run_ocr", lambda path: "")

        result = extractor.extract(make_file("scan.png"), DocumentType.USPS_DOCUMENT)

        assert result.status == ExtractionStatus.FAILED
        assert result.error_message == "OCR returned no text"
        assert result.raw_text == ""

    def test_ocr_receives_file_path(self, make_file, monkeypatch):
        extractor = ImageExtractor()
        calls: list[Path] = []
        monkeypatch.setattr(
            extractor, "_run_ocr", lambda path: calls.append(path) or "text"
        )
        path = make_file("scan.png")

        extractor.extract(path, DocumentType.USPS_DOCUMENT)

        assert calls == [path]


class TestFormExtractor:
    def test_init_without_templates_dir(self):
        assert FormExtractor().templates_dir is None

    def test_init_with_templates_dir(self, tmp_path):
        assert FormExtractor(templates_dir=str(tmp_path)).templates_dir == tmp_path

    def test_no_templates_dir_fails(self, make_file):
        result = FormExtractor().extract(make_file(), DocumentType.LOAN_MODIFICATION)

        assert result.status == ExtractionStatus.FAILED
        assert result.error_message == "No template for loan_modification"

    def test_missing_template_file_fails(self, tmp_path, make_file):
        templates = tmp_path / "templates"
        templates.mkdir()
        extractor = FormExtractor(templates_dir=str(templates))

        result = extractor.extract(make_file(), DocumentType.MI_CERTIFICATE)

        assert result.status == ExtractionStatus.FAILED
        assert result.error_message == "No template for mi_certificate"

    def test_template_found_completes(self, tmp_path, make_file):
        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "copy_of_note.json").write_text("{}")
        extractor = FormExtractor(templates_dir=str(templates))

        result = extractor.extract(make_file("note.pdf"), DocumentType.COPY_OF_NOTE)

        assert result.status == ExtractionStatus.COMPLETED
        assert result.document_id == "note"
        assert result.fields == []

    def test_load_template_returns_type(self, tmp_path):
        (tmp_path / "usps_document.json").write_text("{}")
        extractor = FormExtractor(templates_dir=str(tmp_path))

        assert extractor._load_template(DocumentType.USPS_DOCUMENT) == {
            "type": "usps_document"
        }
