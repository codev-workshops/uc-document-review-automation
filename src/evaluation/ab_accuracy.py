"""Accuracy A/B harness for fuzzy-matching strategies.

Scores a labeled ``(field_type, document_value, record_value,
expected_is_match)`` dataset with every registered algorithm, reports
precision / recall / F1 and a confusion matrix per field type, and sweeps
thresholds to find the best cutoff per algorithm.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

from src.comparators.fuzzy_comparator import FuzzyComparator
from src.comparators.strategies import (
    available_algorithms,
    get_address_strategy,
    get_name_strategy,
)
from src.config.loader import ComparisonConfig

REPO_ROOT = Path(__file__).resolve().parents[2]
LABELED_DATASET_PATH = REPO_ROOT / "tests" / "fixtures" / "labeled_pairs.json"

FIELD_TYPES = ("name", "address")


@dataclass(frozen=True)
class LabeledPair:
    field_type: str
    document_value: str
    record_value: str
    expected_is_match: bool
    source: str = ""
    note: str = ""


@dataclass
class ConfusionMatrix:
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0

    def add(self, predicted: bool, expected: bool) -> None:
        if predicted and expected:
            self.tp += 1
        elif predicted and not expected:
            self.fp += 1
        elif not predicted and expected:
            self.fn += 1
        else:
            self.tn += 1

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 1.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 1.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def accuracy(self) -> float:
        total = self.tp + self.fp + self.tn + self.fn
        return (self.tp + self.tn) / total if total else 1.0

    def as_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "accuracy": round(self.accuracy, 4),
        }


@dataclass
class ScoredPair:
    pair: LabeledPair
    score: float


@dataclass
class SweepPoint:
    threshold: float
    matrix: ConfusionMatrix


def load_labeled_dataset(path: Path = LABELED_DATASET_PATH) -> list[LabeledPair]:
    with path.open(encoding="utf-8") as fh:
        rows = json.load(fh)["rows"]
    return [LabeledPair(**row) for row in rows]


def _comparator_for(algorithm: str) -> FuzzyComparator:
    return FuzzyComparator(
        name_strategy=get_name_strategy(algorithm),
        address_strategy=get_address_strategy(algorithm),
    )


def score_dataset(
    dataset: Iterable[LabeledPair], algorithm: str
) -> dict[str, list[ScoredPair]]:
    comparator = _comparator_for(algorithm)
    scored: dict[str, list[ScoredPair]] = {ft: [] for ft in FIELD_TYPES}
    for pair in dataset:
        if pair.field_type == "name":
            score = comparator.compare_names(pair.document_value, pair.record_value)
        elif pair.field_type == "address":
            score = comparator.compare_addresses(pair.document_value, pair.record_value)
        else:
            raise ValueError(f"unknown field_type {pair.field_type!r}")
        scored[pair.field_type].append(ScoredPair(pair, score))
    return scored


def confusion_at(scored: Iterable[ScoredPair], threshold: float) -> ConfusionMatrix:
    matrix = ConfusionMatrix()
    for sp in scored:
        matrix.add(sp.score >= threshold, sp.pair.expected_is_match)
    return matrix


def threshold_sweep(
    scored: list[ScoredPair],
    start: float = 0.50,
    stop: float = 1.00,
    step: float = 0.01,
) -> list[SweepPoint]:
    points = []
    n = int(round((stop - start) / step))
    for i in range(n + 1):
        t = round(start + i * step, 4)
        points.append(SweepPoint(t, confusion_at(scored, t)))
    return points


def best_threshold(sweep: list[SweepPoint]) -> SweepPoint:
    """Midpoint of the highest-F1 plateau (ties broken by fewest false positives).

    Every threshold on the plateau scores identically on the labeled data;
    taking the middle keeps equal safety margin against unseen near-miss
    negatives (below) and unseen slightly-imperfect positives (above).
    """
    top = max(sweep, key=lambda p: (round(p.matrix.f1, 6), -p.matrix.fp))
    plateau = [
        p
        for p in sweep
        if round(p.matrix.f1, 6) == round(top.matrix.f1, 6) and p.matrix.fp == top.matrix.fp
    ]
    plateau.sort(key=lambda p: p.threshold)
    return plateau[len(plateau) // 2]


def misclassified(scored: list[ScoredPair], threshold: float) -> list[dict[str, Any]]:
    rows = []
    for sp in scored:
        predicted = sp.score >= threshold
        if predicted != sp.pair.expected_is_match:
            rows.append(
                {
                    "document_value": sp.pair.document_value,
                    "record_value": sp.pair.record_value,
                    "score": round(sp.score, 4),
                    "expected": sp.pair.expected_is_match,
                    "kind": "false_positive" if predicted else "false_negative",
                    "note": sp.pair.note,
                }
            )
    return rows


def run_ab(
    config: ComparisonConfig,
    dataset: Optional[list[LabeledPair]] = None,
    algorithms: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Full A/B run -> JSON-serialisable results dict."""
    dataset = dataset if dataset is not None else load_labeled_dataset()
    algorithms = algorithms or available_algorithms()
    active = {"name": config.name_fields, "address": config.address_fields}

    results: dict[str, Any] = {
        "dataset_size": len(dataset),
        "rows_per_field_type": {
            ft: sum(1 for p in dataset if p.field_type == ft) for ft in FIELD_TYPES
        },
        "positives_per_field_type": {
            ft: sum(1 for p in dataset if p.field_type == ft and p.expected_is_match)
            for ft in FIELD_TYPES
        },
        "algorithms": {},
    }
    for algo in algorithms:
        scored = score_dataset(dataset, algo)
        per_field: dict[str, Any] = {}
        for ft in FIELD_TYPES:
            cfg = active[ft]
            configured_threshold = cfg.threshold_for(algo)
            sweep = threshold_sweep(scored[ft])
            best = best_threshold(sweep)
            legacy_threshold = cfg.threshold_for("jaccard")
            per_field[ft] = {
                "configured_threshold": configured_threshold,
                "legacy_threshold": legacy_threshold,
                "at_legacy_threshold": confusion_at(scored[ft], legacy_threshold).as_dict(),
                "at_configured_threshold": confusion_at(
                    scored[ft], configured_threshold
                ).as_dict(),
                "best_threshold": best.threshold,
                "at_best_threshold": best.matrix.as_dict(),
                "sweep": [
                    {"threshold": p.threshold, **p.matrix.as_dict()} for p in sweep
                ],
                "misclassified_at_configured": misclassified(
                    scored[ft], configured_threshold
                ),
                "scores": [
                    {
                        "document_value": sp.pair.document_value,
                        "record_value": sp.pair.record_value,
                        "expected": sp.pair.expected_is_match,
                        "score": round(sp.score, 4),
                    }
                    for sp in scored[ft]
                ],
            }
        results["algorithms"][algo] = per_field
    return results


def _fmt_matrix(m: dict[str, Any]) -> str:
    return (
        f"P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f} "
        f"(TP={m['tp']} FP={m['fp']} TN={m['tn']} FN={m['fn']})"
    )


def render_markdown(results: dict[str, Any]) -> str:
    lines = [
        "# Fuzzy-matching A/B accuracy report",
        "",
        f"Labeled rows: {results['dataset_size']} "
        f"(name={results['rows_per_field_type']['name']}, "
        f"address={results['rows_per_field_type']['address']}; positives "
        f"name={results['positives_per_field_type']['name']}, "
        f"address={results['positives_per_field_type']['address']})",
        "",
        "Dataset: tests/fixtures/labeled_pairs.json. Regenerate with "
        "`python scripts/ab_accuracy_harness.py`.",
        "",
        "## Summary (configured threshold per algorithm)",
        "",
        "| field type | algorithm | threshold | precision | recall | F1 | TP | FP | TN | FN |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for algo, per_field in results["algorithms"].items():
        for ft in FIELD_TYPES:
            r = per_field[ft]
            m = r["at_configured_threshold"]
            lines.append(
                f"| {ft} | {algo} | {r['configured_threshold']:.2f} | {m['precision']:.3f} | "
                f"{m['recall']:.3f} | {m['f1']:.3f} | {m['tp']} | {m['fp']} | "
                f"{m['tn']} | {m['fn']} |"
            )
    lines += [
        "",
        "## Same algorithms at the legacy Jaccard-tuned thresholds",
        "",
        "Shows why the cutoff must travel with the algorithm.",
        "",
        "| field type | algorithm | legacy threshold | precision | recall | F1 | FP | FN |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for algo, per_field in results["algorithms"].items():
        for ft in FIELD_TYPES:
            r = per_field[ft]
            m = r["at_legacy_threshold"]
            lines.append(
                f"| {ft} | {algo} | {r['legacy_threshold']:.2f} | {m['precision']:.3f} | "
                f"{m['recall']:.3f} | {m['f1']:.3f} | {m['fp']} | {m['fn']} |"
            )
    lines += [
        "",
        "## Threshold sweep - best cutoff per algorithm",
        "",
        "| field type | algorithm | best threshold | at best | configured | at configured |",
        "|---|---|---|---|---|---|",
    ]
    for algo, per_field in results["algorithms"].items():
        for ft in FIELD_TYPES:
            r = per_field[ft]
            lines.append(
                f"| {ft} | {algo} | {r['best_threshold']:.2f} | "
                f"{_fmt_matrix(r['at_best_threshold'])} | {r['configured_threshold']:.2f} | "
                f"{_fmt_matrix(r['at_configured_threshold'])} |"
            )
    for algo, per_field in results["algorithms"].items():
        for ft in FIELD_TYPES:
            r = per_field[ft]
            lines += [
                "",
                f"### {ft} / {algo}",
                "",
                "Confusion matrix at configured threshold "
                f"{r['configured_threshold']:.2f}:",
                "",
                "|            | predicted match | predicted mismatch |",
                "|---|---|---|",
                f"| actual match | {r['at_configured_threshold']['tp']} | "
                f"{r['at_configured_threshold']['fn']} |",
                f"| actual mismatch | {r['at_configured_threshold']['fp']} | "
                f"{r['at_configured_threshold']['tn']} |",
                "",
            ]
            mis = r["misclassified_at_configured"]
            if mis:
                lines += ["Misclassified at configured threshold:", ""]
                for row in mis:
                    lines.append(
                        f"- {row['kind']}: '{row['document_value']}' vs "
                        f"'{row['record_value']}' score={row['score']:.3f}"
                        + (f" - {row['note']}" if row["note"] else "")
                    )
                lines.append("")
            lines += [
                "Threshold sweep (every 0.05):",
                "",
                "| threshold | precision | recall | F1 | FP | FN |",
                "|---|---|---|---|---|---|",
            ]
            for p in r["sweep"]:
                if round(p["threshold"] * 100) % 5 == 0:
                    lines.append(
                        f"| {p['threshold']:.2f} | {p['precision']:.3f} | {p['recall']:.3f} | "
                        f"{p['f1']:.3f} | {p['fp']} | {p['fn']} |"
                    )
    lines += [
        "",
        "## All scores",
        "",
    ]
    for ft in FIELD_TYPES:
        algos = list(results["algorithms"])
        lines += [
            f"### {ft}",
            "",
            "| document value | record value | expected | " + " | ".join(algos) + " |",
            "|---|---|---|" + "---|" * len(algos),
        ]
        first = results["algorithms"][algos[0]][ft]["scores"]
        for idx, row in enumerate(first):
            scores = " | ".join(
                f"{results['algorithms'][a][ft]['scores'][idx]['score']:.3f}" for a in algos
            )
            lines.append(
                f"| {row['document_value']} | {row['record_value']} | "
                f"{'match' if row['expected'] else 'mismatch'} | {scores} |"
            )
        lines.append("")
    return "\n".join(lines)
