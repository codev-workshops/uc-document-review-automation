"""PDF document text and table extraction."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.models.document import (
    DocumentType,
    ExtractedField,
    ExtractionResult,
    ExtractionStatus,
)

logger = logging.getLogger(__name__)

# Field patterns expected per document type
DOCUMENT_FIELD_MAP: dict[DocumentType, list[str]] = {
    DocumentType.LOAN_MODIFICATION: [
        "loan_number",
        "borrower_name",
        "modification_date",
        "new_payment_amount",
        "new_interest_rate",
        "new_maturity_date",
        "property_address",
    ],
    DocumentType.MI_CERTIFICATE: [
        "loan_number",
        "certificate_number",
        "coverage_percentage",
        "effective_date",
        "borrower_name",
        "insurer_name",
    ],
    DocumentType.COPY_OF_NOTE: [
        "loan_number",
        "original_amount",
        "interest_rate",
        "maturity_date",
        "borrower_name",
        "property_address",
        "execution_date",
    ],
    DocumentType.ASSUMPTION_AGREEMENT: [
        "loan_number",
        "original_borrower",
        "new_borrower",
        "assumption_date",
        "loan_amount",
        "property_address",
    ],
    DocumentType.USPS_DOCUMENT: [
        "tracking_number",
        "delivery_date",
        "recipient_name",
        "recipient_address",
    ],
    DocumentType.LOAN_HISTORY: [
        "loan_number",
        "origination_date",
        "original_amount",
        "current_balance",
        "payment_history_summary",
    ],
}


class PDFExtractor:
    """Extracts structured fields from PDF documents."""

    def __init__(self, ocr_service_url: Optional[str] = None) -> None:
        self.ocr_service_url = ocr_service_url

    def extract(
        self,
        file_path: Path,
        document_type: DocumentType,
    ) -> ExtractionResult:
        """Extract fields from a PDF file based on expected document type."""
        if not file_path.exists():
            return ExtractionResult(
                document_id=file_path.stem,
                document_type=document_type,
                status=ExtractionStatus.FAILED,
                error_message=f"File not found: {file_path}",
            )

        logger.info("Extracting fields from %s (type=%s)", file_path, document_type.value)

        raw_text = self._extract_raw_text(file_path)
        expected_fields = DOCUMENT_FIELD_MAP.get(document_type, [])
        extracted_fields = self._parse_fields(raw_text, expected_fields)

        return ExtractionResult(
            document_id=file_path.stem,
            document_type=document_type,
            status=ExtractionStatus.COMPLETED,
            fields=extracted_fields,
            raw_text=raw_text,
        )

    def _extract_raw_text(self, file_path: Path) -> str:
        """Extract raw text from a PDF file.

        In production this would use an OCR service (e.g., Azure Form Recognizer)
        or a library like PyMuPDF / pdfplumber. This stub reads text-based PDFs.
        """
        try:
            # Placeholder: in a real implementation, use pdfplumber or OCR
            return f"[Extracted text from {file_path.name}]"
        except Exception as exc:
            logger.error("Text extraction failed for %s: %s", file_path, exc)
            return ""

    @staticmethod
    def _parse_fields(
        raw_text: str,
        expected_fields: list[str],
    ) -> list[ExtractedField]:
        """Parse raw text into structured fields.

        In production, this would use NLP/regex/form-recognizer field mapping.
        """
        fields: list[ExtractedField] = []
        for field_name in expected_fields:
            fields.append(
                ExtractedField(
                    field_name=field_name,
                    field_value="",  # Populated by actual extraction logic
                    confidence=0.0,
                    page_number=1,
                )
            )
        return fields
