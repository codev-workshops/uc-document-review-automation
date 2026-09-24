"""Freeze the golden baseline from the CURRENT (Jaccard) pipeline.

Runs the comparison + decision pipeline over tests/golden/corpus.json with
the Jaccard strategies and legacy thresholds, then persists the
AUTO_APPROVED subset to tests/golden/golden_baseline.json.

Usage: python scripts/build_golden_baseline.py
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config.loader import load_comparison_config  # noqa: E402
from src.evaluation.golden import BASELINE_PATH, write_baseline  # noqa: E402


def main() -> None:
    config = load_comparison_config().with_algorithms(
        name_algorithm="jaccard", address_algorithm="jaccard"
    )
    baseline = write_baseline(config, BASELINE_PATH)
    counts = Counter(baseline["all_decisions"].values())
    print(f"Wrote {BASELINE_PATH}")
    print(f"  corpus: {baseline['corpus_size']} pairs -> {dict(counts)}")
    print(f"  golden AUTO_APPROVED pairs: {len(baseline['golden_pairs'])}")


if __name__ == "__main__":
    main()
