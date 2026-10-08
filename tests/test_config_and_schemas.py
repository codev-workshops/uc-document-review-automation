"""Consistency checks between config/schemas and the code that implements them."""

import json
from pathlib import Path

import pytest
import yaml

from src.agents.comparison_agent import (
    ADDRESS_FIELDS,
    AMOUNT_FIELDS,
    NAME_FIELDS,
    RATE_FIELDS,
)
from src.agents.decision_agent import DEFAULT_CONFIDENCE_THRESHOLD
from src.comparators.field_comparator import CRITICAL_FIELDS, EXACT_MATCH_FIELDS
from src.extractors.pdf_extractor import DOCUMENT_FIELD_MAP
from src.models.document import DocumentType, ExtractionStatus
from src.models.loan_record import CorrectionType

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def rules():
    with open(ROOT / "config" / "comparison_rules.yaml") as f:
        return yaml.safe_load(f)


def _load_schema(name: str) -> dict:
    with open(ROOT / "data" / "schemas" / name) as f:
        return json.load(f)


def test_confidence_threshold_matches_default(rules):
    assert rules["confidence_threshold"] == DEFAULT_CONFIDENCE_THRESHOLD


def test_critical_fields_match(rules):
    assert set(rules["critical_fields"]) == CRITICAL_FIELDS


def test_exact_match_fields_match(rules):
    assert set(rules["field_rules"]["exact_match"]) == EXACT_MATCH_FIELDS


@pytest.mark.parametrize(
    "path, expected",
    [
        (("fuzzy_match", "name_fields"), NAME_FIELDS),
        (("fuzzy_match", "address_fields"), ADDRESS_FIELDS),
        (("amount_fields",), AMOUNT_FIELDS),
        (("rate_fields",), RATE_FIELDS),
    ],
)
def test_field_groups_match(rules, path, expected):
    section = rules["field_rules"]
    for key in path:
        section = section[key]
    assert set(section["fields"]) == expected


@pytest.mark.parametrize("doc_type", ["loan_modification", "mi_certificate"])
def test_document_type_fields_are_extracted(rules, doc_type):
    spec = rules["document_type_fields"][doc_type]
    extracted = set(DOCUMENT_FIELD_MAP[DocumentType(doc_type)])
    assert set(spec["required"]) | set(spec["optional"]) <= extracted


def test_loan_record_schema_correction_types():
    schema = _load_schema("loan_record_schema.json")
    enum = schema["properties"]["correction_type"]["enum"]
    assert set(enum) == {t.value for t in CorrectionType}


def test_extraction_schema_statuses():
    schema = _load_schema("extraction_schema.json")
    enum = schema["properties"]["status"]["enum"]
    assert set(enum) == {s.value for s in ExtractionStatus}


def test_extraction_schema_covers_mapped_document_types():
    schema = _load_schema("extraction_schema.json")
    enum = set(schema["properties"]["document_type"]["enum"])
    assert {t.value for t in DOCUMENT_FIELD_MAP} <= enum


@pytest.mark.xfail(
    strict=True,
    reason="Bug: extraction_schema.json document_type enum omits DocumentType.OTHER ('other')",
)
def test_extraction_schema_covers_all_document_types():
    schema = _load_schema("extraction_schema.json")
    enum = set(schema["properties"]["document_type"]["enum"])
    assert {t.value for t in DocumentType} <= enum
