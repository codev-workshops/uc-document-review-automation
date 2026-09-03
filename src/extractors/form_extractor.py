"""Structured form field extraction for known document templates."""

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


class FormExtractor:
    """Extracts structured fields from known form layouts using template matching."""

    def __init__(self, templates_dir: Optional[str] = None) -> None:
        self.templates_dir = Path(templates_dir) if templates_dir else None

    def extract(
        self,
        file_path: Path,
        document_type: DocumentType,
    ) -> ExtractionResult:
        """Extract form fields using a pre-defined template for the document type."""
        if not file_path.exists():
            return ExtractionResult(
                document_id=file_path.stem,
                document_type=document_type,
                status=ExtractionStatus.FAILED,
                error_message=f"File not found: {file_path}",
            )

        template = self._load_template(document_type)
        if template is None:
            logger.warning(
                "No form template for document type %s, falling back to generic extraction",
                document_type.value,
            )
            return ExtractionResult(
                document_id=file_path.stem,
                document_type=document_type,
                status=ExtractionStatus.FAILED,
                error_message=f"No template for {document_type.value}",
            )

        fields = self._apply_template(file_path, template)
        return ExtractionResult(
            document_id=file_path.stem,
            document_type=document_type,
            status=ExtractionStatus.COMPLETED,
            fields=fields,
        )

    def _load_template(
        self, document_type: DocumentType
    ) -> Optional[dict]:
        """Load the extraction template for a given document type."""
        if self.templates_dir is None:
            return None
        template_file = self.templates_dir / f"{document_type.value}.json"
        if not template_file.exists():
            return None
        # Stub: in production, load and parse the template JSON
        return {"type": document_type.value}

    @staticmethod
    def _apply_template(
        file_path: Path,
        template: dict,
    ) -> list[ExtractedField]:
        """Apply a form template to extract fields at known coordinates."""
        # Stub: in production, use bounding-box coordinates from the template
        return []
