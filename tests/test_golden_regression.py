"""Golden-set regression: previously AUTO_APPROVED pairs must stay approved.

Checks every golden pair under (a) the active config and (b) the Levenshtein
strategies with their calibrated thresholds, asserting BOTH per-field
``is_match`` and ``overall_confidence >= confidence_threshold`` — the
decision can flip on confidence alone even when every field matches.

Any flip is a tripwire: it must be classified in
tests/golden/signed_off_flips.json (``acceptable_correction``) before the
suite goes green. A markdown diff of all flips is written to
reports/golden_flip_report.md on every run.
"""

from pathlib import Path

import pytest

from src.config.loader import ComparisonConfig, FuzzyFieldConfig, load_comparison_config
from src.evaluation.golden import (
    BASELINE_PATH,
    CORPUS_PATH,
    PairSnapshot,
    diff_against_baseline,
    load_baseline,
    load_corpus,
    load_signed_off_flips,
    render_flip_report,
    run_corpus,
)
from src.models.review_result import ReviewDecision

REPORT_PATH = Path(__file__).resolve().parents[1] / "reports" / "golden_flip_report.md"

BASE_CONFIG = load_comparison_config()
CANDIDATES: dict[str, ComparisonConfig] = {
    "active-config": BASE_CONFIG,
    "levenshtein": BASE_CONFIG.with_algorithms(
        name_algorithm="levenshtein", address_algorithm="levenshtein"
    ),
    "levenshtein-names-only": BASE_CONFIG.with_algorithms(name_algorithm="levenshtein"),
    "levenshtein-addresses-only": BASE_CONFIG.with_algorithms(
        address_algorithm="levenshtein"
    ),
}


@pytest.fixture(scope="module")
def baseline():
    assert BASELINE_PATH.is_file(), "run scripts/build_golden_baseline.py"
    return load_baseline()


@pytest.fixture(scope="module")
def corpus():
    return load_corpus(CORPUS_PATH)


@pytest.fixture(scope="module")
def candidate_runs(corpus) -> dict[str, list[PairSnapshot]]:
    return {label: run_corpus(cfg, corpus) for label, cfg in CANDIDATES.items()}


@pytest.fixture(scope="module", autouse=True)
def write_flip_report(baseline, candidate_runs):
    signed = load_signed_off_flips()
    report = render_flip_report(
        baseline,
        {
            label: (CANDIDATES[label], diff_against_baseline(baseline, snaps, signed))
            for label, snaps in candidate_runs.items()
        },
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    yield


def test_baseline_is_frozen_from_jaccard(baseline):
    gen = baseline["generated_with"]
    assert gen["name_algorithm"] == "jaccard"
    assert gen["address_algorithm"] == "jaccard"
    assert len(baseline["golden_pairs"]) > 0


def test_baseline_reproducible_with_jaccard(baseline, corpus):
    """Re-running Jaccard must reproduce the frozen snapshot exactly."""
    cfg = BASE_CONFIG.with_algorithms(name_algorithm="jaccard", address_algorithm="jaccard")
    snaps = {s.pair_id: s for s in run_corpus(cfg, corpus)}
    for raw in baseline["golden_pairs"]:
        golden = PairSnapshot.from_dict(raw)
        assert snaps[golden.pair_id] == golden, golden.pair_id
    assert {s.pair_id: s.decision for s in snaps.values()} == baseline["all_decisions"]


@pytest.mark.parametrize("label", list(CANDIDATES))
def test_golden_pairs_stay_auto_approved(label, baseline, candidate_runs):
    cfg = CANDIDATES[label]
    by_id = {s.pair_id: s for s in candidate_runs[label]}
    signed = load_signed_off_flips()
    failures = []
    for raw in baseline["golden_pairs"]:
        golden = PairSnapshot.from_dict(raw)
        cand = by_id[golden.pair_id]
        if signed.get(golden.pair_id) == "acceptable_correction":
            continue
        field_misses = [f.field_name for f in cand.fields if not f.is_match]
        if field_misses:
            failures.append(f"{golden.pair_id}: per-field mismatch on {field_misses}")
        if cand.overall_confidence < cfg.confidence_threshold:
            failures.append(
                f"{golden.pair_id}: confidence {cand.overall_confidence:.4f} < "
                f"{cfg.confidence_threshold}"
            )
        if cand.decision != ReviewDecision.AUTO_APPROVED.value:
            failures.append(f"{golden.pair_id}: decision flipped to {cand.decision}")
    assert not failures, f"[{label}] regressions (see {REPORT_PATH}):\n" + "\n".join(failures)


def test_flip_tripwire_detects_regression(baseline, corpus):
    """A strict config flips golden pairs; the diff must surface them."""
    strict = ComparisonConfig(
        name_fields=FuzzyFieldConfig(BASE_CONFIG.name_fields.fields, "jaccard", 1.01),
        address_fields=BASE_CONFIG.address_fields,
        amount_fields=BASE_CONFIG.amount_fields,
        rate_fields=BASE_CONFIG.rate_fields,
        amount_tolerance=BASE_CONFIG.amount_tolerance,
        rate_tolerance=BASE_CONFIG.rate_tolerance,
        confidence_threshold=BASE_CONFIG.confidence_threshold,
    )
    flips = diff_against_baseline(baseline, run_corpus(strict, corpus), {"g001": "regression"})
    assert len(flips) == len(baseline["golden_pairs"])
    by_id = {f.pair_id: f for f in flips}
    assert by_id["g001"].signed_off and by_id["g001"].classification == "regression"
    assert not by_id["g002"].signed_off
    assert all(f.candidate_decision == ReviewDecision.MANUAL_REVIEW.value for f in flips)
    assert any(ch["field_name"] == "borrower_name" for ch in by_id["g001"].field_changes)
    report = render_flip_report(baseline, {"strict": (strict, flips)})
    assert f"Flipped decisions: **{len(flips)}**" in report
    assert "g001" in report


@pytest.mark.parametrize("label", list(CANDIDATES))
def test_every_flip_is_signed_off(label, baseline, candidate_runs):
    signed = load_signed_off_flips()
    flips = diff_against_baseline(baseline, candidate_runs[label], signed)
    unsigned = [f.pair_id for f in flips if f.classification != "acceptable_correction"]
    assert not unsigned, (
        f"[{label}] unclassified approved->{[f.candidate_decision for f in flips]} flips: "
        f"{unsigned}. Classify them in tests/golden/signed_off_flips.json; "
        f"details in {REPORT_PATH}"
    )
