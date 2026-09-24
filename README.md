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

### Fuzzy-matching algorithms (`config/comparison_rules.yaml`)

Name and address comparison is driven entirely by `comparison.fuzzy_match` in
`config/comparison_rules.yaml` (override the path with `COMPARISON_RULES_PATH`;
built-in defaults matching this file apply if it is missing). Each of
`name_fields` / `address_fields` selects an `algorithm` and carries a
per-algorithm threshold:

```yaml
name_fields:
  algorithm: jaccard          # active strategy: jaccard | levenshtein
  threshold: 0.85             # cutoff used when no algorithm_thresholds entry exists
  algorithm_thresholds:
    jaccard: 0.85
    levenshtein: 0.97         # calibrated by scripts/ab_accuracy_harness.py
```

Normalization (case folding, name-noise removal, address abbreviation
expansion, Unicode-aware tokenization that preserves hyphens/apostrophes) is a
shared pre-step; only the final scoring function changes per algorithm.

**Default is `jaccard`, so shipping this config is a behavioural no-op.**

#### Rollout: enable Levenshtein

1. Edit `config/comparison_rules.yaml` and set `algorithm: levenshtein` under
   `name_fields` and/or `address_fields`. The calibrated cutoff in
   `algorithm_thresholds.levenshtein` (0.97 names, 0.98 addresses) is picked up
   automatically; do **not** reuse the Jaccard cutoffs — at 0.85/0.80
   Levenshtein produces false positives (see `reports/ab_accuracy_report.md`).
2. Verify before deploying:
   ```bash
   pytest -q                                   # golden regression + A/B calibration tests
   python scripts/ab_accuracy_harness.py       # refreshes reports/ab_accuracy_report.md
   ```
   `tests/test_golden_regression.py` fails if any previously AUTO_APPROVED pair
   in `tests/golden/golden_baseline.json` flips under the active config, unless
   the flip is listed in `tests/golden/signed_off_flips.json` with a
   `classification` (`acceptable_correction` or `regression`) and `signed_off_by`.
   Every run writes `reports/golden_flip_report.md`.
3. Deploy the config change; no code change is required.

#### Rollback

Set `algorithm: jaccard` back (the Jaccard threshold travels with it via
`algorithm_thresholds.jaccard`) and redeploy. Because normalization is shared,
rolling back restores byte-identical pre-Levenshtein scores.

#### Refreshing the golden baseline

Only when a scoring change is intentionally accepted:

```bash
python scripts/build_golden_corpus.py     # deterministic 34-pair corpus
python scripts/build_golden_baseline.py   # always snapshots with jaccard/jaccard
```

## Business Outcomes

- **Operational Efficiency**: Reduce manual review time by up to 70%
- **Cost Avoidance**: Lower operational costs through reduced human intervention
- **Customer Experience**: Faster turnaround on loan corrections and approvals
- **Risk Reduction**: Improved consistency and reduced human error

## Controls

Human-in-the-loop review is enforced for mismatches or low-confidence outcomes. Full audit logging meets compliance requirements. All AI decisions are traceable.

## License

MIT
