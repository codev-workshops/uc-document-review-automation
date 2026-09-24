"""Generate tests/golden/corpus.json — deterministic document/record pairs.

The corpus mixes clean matches, tolerated variations (prefixes, ordering,
abbreviations, Unicode), near-miss typos, and hard mismatches so that the
golden baseline contains both AUTO_APPROVED and non-approved pairs.

Usage: python scripts/build_golden_corpus.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.evaluation.golden import CORPUS_PATH  # noqa: E402

BASE_LOAN = {
    "loan_number": "LN-1002345",
    "loan_amount": 250000.0,
    "interest_rate": 3.5,
    "maturity_date": "2054-06-01",
}


def pair(
    pair_id: str,
    description: str,
    doc_name: str,
    rec_name: str,
    doc_addr: str,
    rec_addr: str,
    correction_type: str = "borrower_name",
    proposed_value: str | None = None,
    doc_overrides: dict[str, str] | None = None,
    record_overrides: dict | None = None,
) -> dict:
    if proposed_value is None:
        proposed_value = rec_name if correction_type == "borrower_name" else rec_addr
    doc_fields = {
        "loan_number": BASE_LOAN["loan_number"],
        "borrower_name": doc_name,
        "property_address": doc_addr,
        "loan_amount": "$250,000.00",
        "interest_rate": "3.500%",
        "maturity_date": "2054-06-01",
    }
    doc_fields.update(doc_overrides or {})
    record = {
        **BASE_LOAN,
        "correction_type": correction_type,
        "current_value": "",
        "proposed_value": proposed_value,
        "borrower_name": rec_name,
        "property_address": rec_addr,
    }
    record.update(record_overrides or {})
    return {
        "pair_id": pair_id,
        "description": description,
        "document": {
            "document_type": "loan_modification",
            "fields": [
                {"field_name": k, "field_value": v, "confidence": 0.98}
                for k, v in doc_fields.items()
            ],
        },
        "record": record,
    }


PAIRS = [
    # --- clean matches -------------------------------------------------
    pair("g001", "identical values", "John Smith", "John Smith",
         "123 Main Street", "123 Main Street"),
    pair("g002", "case differences only", "JOHN SMITH", "john smith",
         "123 MAIN ST", "123 Main St"),
    pair("g003", "prefix/suffix noise", "Mr. John Smith Jr.", "John Smith",
         "123 Main Street", "123 Main Street"),
    pair("g004", "reordered name tokens", "Smith John", "John Smith",
         "123 Main Street", "123 Main Street"),
    pair("g005", "address abbreviation", "Maria Garcia", "Maria Garcia",
         "456 North Oak Avenue", "456 N Oak Ave"),
    pair("g006", "address punctuation", "Maria Garcia", "Maria Garcia",
         "456 N. Oak Ave., Apt. 3", "456 N Oak Ave Apt 3"),
    pair("g007", "hyphenated name", "Jean-Luc Picard", "Jean-Luc Picard",
         "789 Elm Boulevard", "789 Elm Blvd"),
    pair("g008", "apostrophe name, curly vs straight", "Conor O\u2019Brien",
         "Conor O'Brien", "12 Court Place", "12 Ct Pl"),
    pair("g009", "unicode accented name", "Jos\u00e9 Mu\u00f1oz", "JOS\u00c9 MU\u00d1OZ",
         "34 South River Road", "34 S River Rd"),
    pair("g010", "suite abbreviation", "Alice Johnson", "Alice Johnson",
         "100 Commerce Drive Suite 200", "100 Commerce Dr Ste 200"),
    pair("g011", "address correction type", "Wei Chen", "Wei Chen",
         "55 Lake Circle", "55 Lake Cir", correction_type="property_address"),
    pair("g012", "loan amount correction", "Wei Chen", "Wei Chen",
         "55 Lake Circle", "55 Lake Cir", correction_type="loan_amount",
         proposed_value="250000.00"),
    pair("g013", "interest rate correction", "Wei Chen", "Wei Chen",
         "55 Lake Circle", "55 Lake Cir", correction_type="interest_rate",
         proposed_value="3.5"),
    pair("g014", "three-token name with middle initial both sides", "Robert A Lee",
         "Robert A. Lee", "9 West Lane", "9 W Ln"),
    pair("g015", "Dr prefix, building abbreviation", "Dr. Priya Natarajan",
         "Priya Natarajan", "200 Tech Building 4", "200 Tech Bldg 4"),
    pair("g016", "II suffix noise", "Henry Ford II", "Henry Ford",
         "1 Ford Road", "1 Ford Rd"),
    pair("g017", "cyrillic name",
         "\u0412\u043b\u0430\u0434\u0438\u043c\u0438\u0440 \u041f\u0435\u0442\u0440\u043e\u0432",
         "\u0432\u043b\u0430\u0434\u0438\u043c\u0438\u0440 \u043f\u0435\u0442\u0440\u043e\u0432",
         "77 East Street", "77 E St"),
    pair("g018", "extra whitespace", "  Alice   Johnson ", "Alice Johnson",
         "100  Commerce   Dr", "100 Commerce Dr"),
    # --- near misses (Jaccard fails, Levenshtein may accept) -----------
    pair("n001", "single-letter typo in first name", "Jon Smith", "John Smith",
         "123 Main Street", "123 Main Street"),
    pair("n002", "transposed letters in surname", "Maria Gracia", "Maria Garcia",
         "456 N Oak Ave", "456 N Oak Ave"),
    pair("n003", "missing middle initial", "Robert Lee", "Robert A Lee",
         "9 W Ln", "9 W Ln"),
    pair("n004", "house number off by one digit", "Alice Johnson", "Alice Johnson",
         "100 Commerce Dr", "101 Commerce Dr"),
    pair("n005", "extra unit in document address", "Wei Chen", "Wei Chen",
         "55 Lake Cir Unit B", "55 Lake Cir"),
    pair("n006", "double letter dropped", "Jonathan Harris", "Jonathan Haris",
         "8 Pine Court", "8 Pine Ct"),
    pair("n007", "accent stripped by OCR", "Jose Munoz", "Jos\u00e9 Mu\u00f1oz",
         "34 S River Rd", "34 S River Rd"),
    pair("n008", "hyphen dropped", "Jean Luc Picard", "Jean-Luc Picard",
         "789 Elm Blvd", "789 Elm Blvd"),
    # --- hard mismatches -----------------------------------------------
    pair("m001", "different borrower", "Jane Doe", "John Smith",
         "123 Main Street", "123 Main Street"),
    pair("m002", "different address", "John Smith", "John Smith",
         "123 Main Street", "789 Elm Boulevard"),
    pair("m003", "critical loan amount mismatch", "John Smith", "John Smith",
         "123 Main Street", "123 Main Street",
         doc_overrides={"loan_amount": "$260,000.00"}),
    pair("m004", "critical loan number mismatch", "John Smith", "John Smith",
         "123 Main Street", "123 Main Street",
         doc_overrides={"loan_number": "LN-9999999"}),
    pair("m005", "critical interest rate mismatch", "John Smith", "John Smith",
         "123 Main Street", "123 Main Street",
         doc_overrides={"interest_rate": "4.000%"}),
    pair("m006", "same surname different person", "Michael Smith", "John Smith",
         "123 Main Street", "123 Main Street"),
    pair("m007", "same street different city number", "Alice Johnson", "Alice Johnson",
         "100 Commerce Dr", "900 Commerce Dr Suite 1"),
    pair("m008", "empty document name", "", "John Smith",
         "123 Main Street", "123 Main Street"),
]


def main() -> None:
    ids = [p["pair_id"] for p in PAIRS]
    assert len(ids) == len(set(ids)), "duplicate pair ids"
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CORPUS_PATH.write_text(
        json.dumps({"pairs": PAIRS}, indent=2, ensure_ascii=False) + "\n", "utf-8"
    )
    print(f"Wrote {len(PAIRS)} pairs to {CORPUS_PATH}")


if __name__ == "__main__":
    main()
