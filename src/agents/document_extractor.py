"""Document Extraction Agent — parses and extracts structured data from diverse document types."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.extractors.form_extractor import FormExtractor
from src.extractors.image_extractor import ImageExtractor
from src.extractors.pdf_extractor import PDFExtractor
from src.models.document import (
    DocumentMetadata,
    DocumentType,
    ExtractionResult,
    ExtractionStatus,
)

logger = logging.getLogger(__name__)

# Map MIME types to the appropriate extractor
MIME_EXTRACTORS = {
    "application/pdf": "pdf",
    "image/jpeg": "image",
    "image/png": "image",
    "image/tiff": "image",
}


class DocumentExtractionAgent:
    """Orchestrates document extraction across multiple extractor backends."""

    def __init__(
        self,
        ocr_service_url: Optional[str] = None,
        ocr_api_key: Optional[str] = None,
        templates_dir: Optional[str] = None,
    ) -> None:
        self.pdf_extractor = PDFExtractor(ocr_service_url=ocr_service_url)
        self.image_extractor = ImageExtractor(
            ocr_service_url=ocr_service_url,
            ocr_api_key=ocr_api_key,
        )
        self.form_extractor = FormExtractor(templates_dir=templates_dir)

    def extract_document(
        self,
        file_path: Path,
        metadata: DocumentMetadata,
    ) -> ExtractionResult:
        """Extract structured data from a document based on its type and format."""
        logger.info(
            "Processing document %s (type=%s, mime=%s)",
            metadata.document_id,
            metadata.document_type.value,
            metadata.mime_type,
        )

        extractor_type = MIME_EXTRACTORS.get(metadata.mime_type)
        if extractor_type is None:
            return ExtractionResult(
                document_id=metadata.document_id,
                document_type=metadata.document_type,
                status=ExtractionStatus.FAILED,
                error_message=f"Unsupported MIME type: {metadata.mime_type}",
            )

        # Try form-based extraction first (higher accuracy for known templates)
        result = self.form_extractor.extract(file_path, metadata.document_type)
        if result.status == ExtractionStatus.COMPLETED and result.fields:
            result.extraction_timestamp = datetime.utcnow()
            logger.info(
                "Form extraction succeeded for %s (%d fields)",
                metadata.document_id,
                len(result.fields),
            )
            return result

        # Fall back to PDF or image extraction
        if extractor_type == "pdf":
            result = self.pdf_extractor.extract(file_path, metadata.document_type)
        else:
            result = self.image_extractor.extract(file_path, metadata.document_type)

        result.extraction_timestamp = datetime.utcnow()
        return result

    def extract_batch(
        self,
        documents: list[tuple[Path, DocumentMetadata]],
    ) -> list[ExtractionResult]:
        """Extract data from a batch of documents."""
        results: list[ExtractionResult] = []
        for file_path, metadata in documents:
            result = self.extract_document(file_path, metadata)
            results.append(result)
        return results
