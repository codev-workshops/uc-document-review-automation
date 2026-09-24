"""Tests for the A/B accuracy harness and the calibrated thresholds it backs."""

from src.config.loader import load_comparison_config
from src.evaluation.ab_accuracy import (
    ConfusionMatrix,
    LabeledPair,
    ScoredPair,
    best_threshold,
    confusion_at,
    load_labeled_dataset,
    render_markdown,
    run_ab,
    score_dataset,
    threshold_sweep,
)


def _sp(score: float, expected: bool) -> ScoredPair:
    return ScoredPair(LabeledPair("name", "a", "b", expected), score)


class TestMetrics:
    def test_confusion_matrix_counts(self):
        m = ConfusionMatrix()
        for predicted, expected in [(True, True), (True, False), (False, True), (False, False)]:
            m.add(predicted, expected)
        assert (m.tp, m.fp, m.fn, m.tn) == (1, 1, 1, 1)
        assert m.precision == 0.5 and m.recall == 0.5 and m.f1 == 0.5 and m.accuracy == 0.5

    def test_empty_matrix_has_no_errors(self):
        m = ConfusionMatrix()
        assert m.precision == 1.0 and m.recall == 1.0 and m.f1 == 1.0

    def test_confusion_at_threshold(self):
        scored = [_sp(1.0, True), _sp(0.9, False), _sp(0.7, True), _sp(0.2, False)]
        m = confusion_at(scored, 0.8)
        assert (m.tp, m.fp, m.fn, m.tn) == (1, 1, 1, 1)

    def test_sweep_and_best_threshold(self):
        scored = [_sp(1.0, True), _sp(0.95, True), _sp(0.6, False), _sp(0.2, False)]
        sweep = threshold_sweep(scored)
        assert sweep[0].threshold == 0.5 and sweep[-1].threshold == 1.0
        best = best_threshold(sweep)
        assert best.matrix.f1 == 1.0
        assert 0.61 <= best.threshold <= 0.95


class TestDataset:
    def test_dataset_loads_and_covers_both_field_types(self):
        rows = load_labeled_dataset()
        types = {r.field_type for r in rows}
        assert types == {"name", "address"}
        assert any(r.expected_is_match for r in rows)
        assert any(not r.expected_is_match for r in rows)

    def test_dataset_seeded_from_existing_tests(self):
        rows = load_labeled_dataset()
        assert any(r.source.startswith("tests/test_comparators.py") for r in rows)

    def test_scores_in_unit_range(self):
        for algo in ("jaccard", "levenshtein"):
            for scored in score_dataset(load_labeled_dataset(), algo).values():
                assert all(0.0 <= sp.score <= 1.0 for sp in scored)


class TestCalibration:
    def test_configured_thresholds_are_lossless_on_labeled_data(self):
        """Committed YAML thresholds must reproduce every label for both algorithms."""
        results = run_ab(load_comparison_config())
        for algo, per_field in results["algorithms"].items():
            for ft, r in per_field.items():
                m = r["at_configured_threshold"]
                assert m["fp"] == 0 and m["fn"] == 0, (algo, ft, r["misclassified_at_configured"])

    def test_levenshtein_needs_recalibration_vs_legacy_threshold(self):
        results = run_ab(load_comparison_config())
        lev = results["algorithms"]["levenshtein"]
        assert lev["name"]["at_legacy_threshold"]["fp"] > 0
        assert lev["address"]["at_legacy_threshold"]["fp"] > 0

    def test_report_renders(self):
        report = render_markdown(run_ab(load_comparison_config()))
        assert "## Summary" in report
        assert "levenshtein" in report and "jaccard" in report
