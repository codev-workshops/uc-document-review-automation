"""OCR-based image document extraction."""

import logging
from pathlib import Path
from typing import Optional

from src.models.document import (
    DocumentType,
    ExtractedField,
    ExtractionResult,
    ExtractionStatus,
)

logger = logging.getLogger(__name__)


class ImageExtractor:
    """Extracts text and structured data from scanned document images."""

    def __init__(
        self,
        ocr_service_url: Optional[str] = None,
        ocr_api_key: Optional[str] = None,
    ) -> None:
        self.ocr_service_url = ocr_service_url
        self.ocr_api_key = ocr_api_key

    def extract(
        self,
        file_path: Path,
        document_type: DocumentType,
    ) -> ExtractionResult:
        """Extract fields from an image file using OCR."""
        if not file_path.exists():
            return ExtractionResult(
                document_id=file_path.stem,
                document_type=document_type,
                status=ExtractionStatus.FAILED,
                error_message=f"File not found: {file_path}",
            )

        logger.info("Running OCR on %s (type=%s)", file_path, document_type.value)

        raw_text = self._run_ocr(file_path)
        if not raw_text:
            return ExtractionResult(
                document_id=file_path.stem,
                document_type=document_type,
                status=ExtractionStatus.FAILED,
                error_message="OCR returned no text",
            )

        return ExtractionResult(
            document_id=file_path.stem,
            document_type=document_type,
            status=ExtractionStatus.COMPLETED,
            fields=[],
            raw_text=raw_text,
        )

    def _run_ocr(self, file_path: Path) -> str:
        """Send an image to the OCR service and return extracted text.

        In production, this calls Azure Form Recognizer, AWS Textract,
        or Google Document AI.
        """
        # Stub implementation
        logger.info("OCR service call for %s (stub)", file_path.name)
        return f"[OCR text from {file_path.name}]"
