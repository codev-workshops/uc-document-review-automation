"""Golden-set regression harness.

Runs the comparison + decision pipeline over a corpus of document/record
pairs, snapshots per-field results and the final ``ReviewDecision``, and
diffs a candidate configuration against a frozen baseline.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from src.agents.comparison_agent import ComparisonAgent
from src.agents.decision_agent import DecisionAgent
from src.config.loader import ComparisonConfig
from src.models.document import (
    DocumentType,
    ExtractedField,
    ExtractionResult,
    ExtractionStatus,
)
from src.models.loan_record import CorrectionType, LoanCorrectionRecord
from src.models.review_result import ReviewDecision

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = REPO_ROOT / "tests" / "golden"
CORPUS_PATH = GOLDEN_DIR / "corpus.json"
BASELINE_PATH = GOLDEN_DIR / "golden_baseline.json"
SIGNED_OFF_FLIPS_PATH = GOLDEN_DIR / "signed_off_flips.json"


@dataclass
class FieldSnapshot:
    field_name: str
    document_value: str
    record_value: str
    similarity_score: float
    is_match: bool


@dataclass
class PairSnapshot:
    pair_id: str
    description: str
    decision: str
    overall_confidence: float
    fields: list[FieldSnapshot] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PairSnapshot":
        return cls(
            pair_id=data["pair_id"],
            description=data.get("description", ""),
            decision=data["decision"],
            overall_confidence=data["overall_confidence"],
            fields=[FieldSnapshot(**f) for f in data.get("fields", [])],
        )


@dataclass
class Flip:
    pair_id: str
    description: str
    baseline_decision: str
    candidate_decision: str
    baseline_confidence: float
    candidate_confidence: float
    field_changes: list[dict[str, Any]]
    signed_off: bool = False
    classification: Optional[str] = None


def load_corpus(path: Path = CORPUS_PATH) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)["pairs"]


def _build_extraction(pair: dict[str, Any]) -> ExtractionResult:
    doc = pair["document"]
    return ExtractionResult(
        document_id=doc.get("document_id", f"doc-{pair['pair_id']}"),
        document_type=DocumentType(doc.get("document_type", "other")),
        status=ExtractionStatus.COMPLETED,
        fields=[
            ExtractedField(
                field_name=f["field_name"],
                field_value=f["field_value"],
                confidence=f.get("confidence", 0.99),
            )
            for f in doc["fields"]
        ],
    )


def _build_record(pair: dict[str, Any]) -> LoanCorrectionRecord:
    rec = pair["record"]
    maturity = rec.get("maturity_date")
    return LoanCorrectionRecord(
        correction_id=rec.get("correction_id", f"corr-{pair['pair_id']}"),
        loan_number=rec["loan_number"],
        correction_type=CorrectionType(rec["correction_type"]),
        current_value=rec.get("current_value", ""),
        proposed_value=rec["proposed_value"],
        submitted_by=rec.get("submitted_by", "golden-harness"),
        submitted_at=datetime(2026, 1, 1),
        borrower_name=rec.get("borrower_name", ""),
        property_address=rec.get("property_address", ""),
        loan_amount=rec.get("loan_amount"),
        interest_rate=rec.get("interest_rate"),
        maturity_date=date.fromisoformat(maturity) if maturity else None,
    )


def run_pair(
    pair: dict[str, Any],
    comparison_agent: ComparisonAgent,
    decision_agent: DecisionAgent,
) -> PairSnapshot:
    extraction = _build_extraction(pair)
    record = _build_record(pair)
    comparisons = comparison_agent.compare(extraction, record)
    result = decision_agent.decide(record.correction_id, record.loan_number, comparisons)
    return PairSnapshot(
        pair_id=pair["pair_id"],
        description=pair.get("description", ""),
        decision=result.decision.value,
        overall_confidence=round(result.overall_confidence, 6),
        fields=[
            FieldSnapshot(
                field_name=c.field_name,
                document_value=c.document_value,
                record_value=c.record_value,
                similarity_score=round(c.similarity_score, 6),
                is_match=c.is_match,
            )
            for c in comparisons
        ],
    )


def run_corpus(
    config: ComparisonConfig, corpus: Optional[list[dict[str, Any]]] = None
) -> list[PairSnapshot]:
    corpus = corpus if corpus is not None else load_corpus()
    comparison_agent = ComparisonAgent(config)
    decision_agent = DecisionAgent(confidence_threshold=config.confidence_threshold)
    return [run_pair(pair, comparison_agent, decision_agent) for pair in corpus]


def build_baseline(config: ComparisonConfig) -> dict[str, Any]:
    """Snapshot the full corpus and freeze the AUTO_APPROVED subset as golden."""
    snapshots = run_corpus(config)
    approved = [s for s in snapshots if s.decision == ReviewDecision.AUTO_APPROVED.value]
    return {
        "generated_with": {
            "name_algorithm": config.name_fields.algorithm,
            "name_threshold": config.name_fields.threshold,
            "address_algorithm": config.address_fields.algorithm,
            "address_threshold": config.address_fields.threshold,
            "confidence_threshold": config.confidence_threshold,
        },
        "corpus_size": len(snapshots),
        "all_decisions": {s.pair_id: s.decision for s in snapshots},
        "golden_pairs": [asdict(s) for s in approved],
    }


def write_baseline(config: ComparisonConfig, path: Path = BASELINE_PATH) -> dict[str, Any]:
    baseline = build_baseline(config)
    path.write_text(json.dumps(baseline, indent=2, ensure_ascii=False) + "\n", "utf-8")
    return baseline


def load_baseline(path: Path = BASELINE_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_signed_off_flips(path: Path = SIGNED_OFF_FLIPS_PATH) -> dict[str, str]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as fh:
        return {f["pair_id"]: f["classification"] for f in json.load(fh)["flips"]}


def diff_against_baseline(
    baseline: dict[str, Any],
    candidate: list[PairSnapshot],
    signed_off: Optional[dict[str, str]] = None,
) -> list[Flip]:
    """Return one ``Flip`` for every golden pair that is no longer AUTO_APPROVED."""
    signed_off = signed_off or {}
    by_id = {s.pair_id: s for s in candidate}
    flips: list[Flip] = []
    for raw in baseline["golden_pairs"]:
        golden = PairSnapshot.from_dict(raw)
        cand = by_id.get(golden.pair_id)
        if cand is None:
            raise KeyError(f"golden pair {golden.pair_id} missing from corpus")
        if cand.decision == ReviewDecision.AUTO_APPROVED.value:
            continue
        cand_fields = {f.field_name: f for f in cand.fields}
        changes = []
        for gf in golden.fields:
            cf = cand_fields.get(gf.field_name)
            if (
                cf is None
                or cf.is_match != gf.is_match
                or cf.similarity_score != gf.similarity_score
            ):
                changes.append(
                    {
                        "field_name": gf.field_name,
                        "document_value": gf.document_value,
                        "record_value": gf.record_value,
                        "baseline": {"score": gf.similarity_score, "is_match": gf.is_match},
                        "candidate": None
                        if cf is None
                        else {"score": cf.similarity_score, "is_match": cf.is_match},
                    }
                )
        flips.append(
            Flip(
                pair_id=golden.pair_id,
                description=golden.description,
                baseline_decision=golden.decision,
                candidate_decision=cand.decision,
                baseline_confidence=golden.overall_confidence,
                candidate_confidence=cand.overall_confidence,
                field_changes=changes,
                signed_off=golden.pair_id in signed_off,
                classification=signed_off.get(golden.pair_id),
            )
        )
    return flips


def render_flip_report(
    baseline: dict[str, Any],
    candidates: dict[str, tuple[ComparisonConfig, list[Flip]]],
) -> str:
    """Markdown diff report of approved -> manual/rejected flips per candidate."""
    gen = baseline["generated_with"]
    lines = [
        "# Golden-set flip report",
        "",
        f"Baseline: name={gen['name_algorithm']}@{gen['name_threshold']}, "
        f"address={gen['address_algorithm']}@{gen['address_threshold']}, "
        f"confidence>={gen['confidence_threshold']}",
        f"Corpus size: {baseline['corpus_size']}; golden (AUTO_APPROVED) pairs: "
        f"{len(baseline['golden_pairs'])}",
        "",
        "A *flip* is a golden pair whose decision is no longer AUTO_APPROVED under the",
        "candidate configuration. Flips are a tripwire: each must be classified as an",
        "acceptable correction or a regression in tests/golden/signed_off_flips.json.",
        "",
    ]
    for label, (cfg, flips) in candidates.items():
        lines += [
            f"## Candidate: {label}",
            "",
            f"name={cfg.name_fields.algorithm}@{cfg.name_fields.threshold}, "
            f"address={cfg.address_fields.algorithm}@{cfg.address_fields.threshold}",
            "",
            f"Flipped decisions: **{len(flips)}** "
            f"(unsigned: {sum(1 for f in flips if not f.signed_off)})",
            "",
        ]
        if not flips:
            lines += ["No flips - every golden pair still resolves to AUTO_APPROVED.", ""]
            continue
        lines += [
            "| pair | baseline | candidate | conf (base -> cand) | signed off | classification |",
            "|---|---|---|---|---|---|",
        ]
        for f in flips:
            lines.append(
                f"| {f.pair_id} | {f.baseline_decision} | {f.candidate_decision} | "
                f"{f.baseline_confidence:.4f} -> {f.candidate_confidence:.4f} | "
                f"{'yes' if f.signed_off else 'NO'} | {f.classification or '-'} |"
            )
        lines.append("")
        for f in flips:
            lines += [f"### {f.pair_id}: {f.description}", ""]
            for ch in f.field_changes:
                cand = ch["candidate"]
                cand_txt = (
                    "missing"
                    if cand is None
                    else f"{cand['score']:.4f} ({'match' if cand['is_match'] else 'MISMATCH'})"
                )
                lines.append(
                    f"- `{ch['field_name']}`: '{ch['document_value']}' vs "
                    f"'{ch['record_value']}' - baseline {ch['baseline']['score']:.4f} "
                    f"({'match' if ch['baseline']['is_match'] else 'MISMATCH'}) -> "
                    f"candidate {cand_txt}"
                )
            lines.append("")
    return "\n".join(lines)
