# Automated Document Review for Loan Processing

## Overview

This project automates document review to validate customer-submitted corrections in loan processing workflows. It uses agentic AI to extract data from uploaded documents, compare it against loan correction records, and return match results for automated decisioning or exception routing.

## Problem Statement

Internal users manually review and compare multiple customer-uploaded documents (e.g., copy of note, loan modification, MI certificate, USPS documents, assumption agreement, loan history). This process is time-intensive, error-prone, and increasingly unsustainable as loan volumes grow.

## Architecture

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│  Document Extraction│────▶│  Comparison           │────▶│  Decision           │
│  Agent              │     │  Agent                │     │  Agent              │
└─────────────────────┘     └──────────────────────┘     └─────────┬───────────┘
                                                                    │
                                                          ┌─────────▼───────────┐
                                                          │  Audit              │
                                                          │  Agent              │
                                                          └─────────────────────┘
```

### Agent Responsibilities

| Agent | Role |
|-------|------|
| **Document Extraction Agent** | Parses and extracts structured data from diverse document types (PDF, images, scanned docs) |
| **Comparison Agent** | Validates extracted data against loan correction records |
| **Decision Agent** | Determines auto-approval eligibility or routes exceptions for manual review |
| **Audit Agent** | Logs all AI decisions and comparisons for compliance and traceability |

## Project Structure

```
├── src/
│   ├── agents/                      # Agent implementations
│   │   ├── document_extractor.py    # Document parsing and data extraction
│   │   ├── comparison_agent.py      # Data comparison and validation
│   │   ├── decision_agent.py        # Auto-approval / exception routing
│   │   └── audit_agent.py           # Compliance logging
│   ├── extractors/                  # Document-type-specific extractors
│   │   ├── pdf_extractor.py         # PDF text and table extraction
│   │   ├── image_extractor.py       # OCR-based image extraction
│   │   └── form_extractor.py        # Structured form field extraction
│   ├── comparators/                 # Comparison strategies
│   │   ├── field_comparator.py      # Field-level comparison
│   │   ├── fuzzy_comparator.py      # Fuzzy matching for name/address
│   │   └── amount_comparator.py     # Numeric/currency comparison
│   ├── models/                      # Data models
│   │   ├── document.py              # Document metadata and content models
│   │   ├── loan_record.py           # Loan correction record models
│   │   └── review_result.py         # Review decision models
│   └── utils/                       # Shared utilities
│       ├── ocr_client.py            # OCR service client
│       └── storage_client.py        # Document storage client
├── data/
│   ├── sample_documents/            # Sample loan documents for testing
│   │   ├── loan_modification.pdf    # Sample loan modification letter
│   │   ├── mi_certificate.pdf       # Sample MI certificate
│   │   └── assumption_agreement.pdf # Sample assumption agreement
│   └── schemas/                     # Document and data schemas
│       ├── loan_record_schema.json  # Loan correction record schema
│       └── extraction_schema.json   # Extracted data schema
├── config/
│   └── comparison_rules.yaml        # Comparison thresholds and rules
├── tests/                           # Test suite
├── docs/                            # Documentation
├── requirements.txt
├── Dockerfile
└── .gitignore
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run extraction on a sample document
python -m src.agents.document_extractor --input data/sample_documents/loan_modification.pdf

# Run comparison against a loan record
python -m src.agents.comparison_agent --document data/sample_documents/ --record data/schemas/loan_record_schema.json

# Run the full review pipeline
python -m src.agents.decision_agent --input data/sample_documents/ --records data/schemas/
```

## Configuration

Set the following environment variables (see `.env.example`):

| Variable | Description |
|----------|-------------|
| `OCR_SERVICE_URL` | OCR service endpoint (e.g., Azure Form Recognizer) |
| `OCR_API_KEY` | OCR service API key |
| `STORAGE_BACKEND` | Document storage backend (local, s3, azure) |
| `CONFIDENCE_THRESHOLD` | Minimum confidence for auto-approval (default: 0.95) |
| `AUDIT_LOG_PATH` | Path for audit log output |

## Business Outcomes

- **Operational Efficiency**: Reduce manual review time by up to 70%
- **Cost Avoidance**: Lower operational costs through reduced human intervention
- **Customer Experience**: Faster turnaround on loan corrections and approvals
- **Risk Reduction**: Improved consistency and reduced human error

## Controls

Human-in-the-loop review is enforced for mismatches or low-confidence outcomes. Full audit logging meets compliance requirements. All AI decisions are traceable.

## License

MIT
