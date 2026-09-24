"""Run the fuzzy-matching A/B accuracy harness and write reports.

Outputs reports/ab_accuracy_report.md and reports/ab_accuracy_results.json.

Usage: python scripts/ab_accuracy_harness.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config.loader import load_comparison_config  # noqa: E402
from src.evaluation.ab_accuracy import FIELD_TYPES, render_markdown, run_ab  # noqa: E402

REPORT_DIR = REPO_ROOT / "reports"


def main() -> None:
    results = run_ab(load_comparison_config())
    REPORT_DIR.mkdir(exist_ok=True)
    (REPORT_DIR / "ab_accuracy_report.md").write_text(render_markdown(results), "utf-8")
    (REPORT_DIR / "ab_accuracy_results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n", "utf-8"
    )
    for algo, per_field in results["algorithms"].items():
        for ft in FIELD_TYPES:
            r = per_field[ft]
            m = r["at_configured_threshold"]
            b = r["at_best_threshold"]
            print(
                f"{ft:8s} {algo:12s} configured={r['configured_threshold']:.2f} "
                f"F1={m['f1']:.3f} FP={m['fp']} FN={m['fn']} | "
                f"best={r['best_threshold']:.2f} F1={b['f1']:.3f} FP={b['fp']} FN={b['fn']}"
            )
    print(f"Wrote {REPORT_DIR / 'ab_accuracy_report.md'}")


if __name__ == "__main__":
    main()
