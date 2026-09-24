"""Tests for config loading and config-driven strategy selection."""

from pathlib import Path

import pytest
import yaml

from src.agents.comparison_agent import ComparisonAgent
from src.comparators.strategies import (
    JaccardAddressStrategy,
    JaccardNameStrategy,
    LevenshteinAddressStrategy,
    LevenshteinNameStrategy,
)
from src.config.loader import (
    DEFAULT_CONFIG_PATH,
    ComparisonConfig,
    load_comparison_config,
    parse_comparison_config,
)


def _write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "rules.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


class TestLoader:
    def test_default_file_matches_legacy_behaviour(self):
        cfg = load_comparison_config()
        assert cfg.source_path == DEFAULT_CONFIG_PATH
        assert cfg.name_fields.algorithm == "jaccard"
        assert cfg.name_fields.threshold == 0.85
        assert cfg.address_fields.algorithm == "jaccard"
        assert cfg.address_fields.threshold == 0.80
        assert cfg.name_fields.fields == {
            "borrower_name",
            "original_borrower",
            "new_borrower",
            "recipient_name",
        }
        assert cfg.address_fields.fields == {"property_address", "recipient_address"}
        assert cfg.amount_fields == {
            "loan_amount",
            "original_amount",
            "current_balance",
            "new_payment_amount",
        }
        assert cfg.rate_fields == {
            "interest_rate",
            "new_interest_rate",
            "coverage_percentage",
        }
        assert cfg.confidence_threshold == 0.95

    def test_default_file_has_calibrated_threshold_per_algorithm(self):
        cfg = load_comparison_config()
        assert set(cfg.name_fields.algorithm_thresholds) == {"jaccard", "levenshtein"}
        assert set(cfg.address_fields.algorithm_thresholds) == {"jaccard", "levenshtein"}

    def test_missing_file_falls_back_to_defaults(self, tmp_path):
        cfg = load_comparison_config(tmp_path / "nope.yaml")
        assert cfg == ComparisonConfig.defaults()

    def test_env_var_path(self, tmp_path, monkeypatch):
        path = _write_config(
            tmp_path,
            {"field_rules": {"fuzzy_match": {"name_fields": {"threshold": 0.5}}}},
        )
        monkeypatch.setenv("COMPARISON_RULES_PATH", str(path))
        assert load_comparison_config().name_fields.threshold == 0.5

    def test_partial_config_keeps_defaults(self):
        cfg = parse_comparison_config({"confidence_threshold": 0.9})
        assert cfg.confidence_threshold == 0.9
        assert cfg.name_fields == ComparisonConfig.defaults().name_fields

    def test_threshold_travels_with_algorithm(self):
        cfg = parse_comparison_config(
            {
                "field_rules": {
                    "fuzzy_match": {
                        "name_fields": {
                            "algorithm": "levenshtein",
                            "algorithm_thresholds": {"jaccard": 0.85, "levenshtein": 0.9},
                        }
                    }
                }
            }
        )
        assert cfg.name_fields.algorithm == "levenshtein"
        assert cfg.name_fields.threshold == 0.9
        assert cfg.name_fields.threshold_for("jaccard") == 0.85

    def test_with_algorithms_swaps_threshold(self):
        base = load_comparison_config()
        flipped = base.with_algorithms(name_algorithm="levenshtein")
        assert flipped.name_fields.algorithm == "levenshtein"
        assert flipped.name_fields.threshold == base.name_fields.threshold_for(
            "levenshtein"
        )
        assert flipped.address_fields == base.address_fields


class TestConfigDrivenAgent:
    def test_default_agent_uses_jaccard(self):
        agent = ComparisonAgent()
        assert isinstance(agent.fuzzy_comparator.name_strategy, JaccardNameStrategy)
        assert isinstance(agent.fuzzy_comparator.address_strategy, JaccardAddressStrategy)

    def test_flipping_config_changes_active_strategy(self, tmp_path):
        path = _write_config(
            tmp_path,
            {
                "field_rules": {
                    "fuzzy_match": {
                        "name_fields": {"algorithm": "levenshtein", "threshold": 0.9},
                        "address_fields": {"algorithm": "levenshtein", "threshold": 0.88},
                    }
                }
            },
        )
        agent = ComparisonAgent(load_comparison_config(path))
        assert isinstance(agent.fuzzy_comparator.name_strategy, LevenshteinNameStrategy)
        assert isinstance(
            agent.fuzzy_comparator.address_strategy, LevenshteinAddressStrategy
        )
        assert agent.config.name_fields.threshold == 0.9
        assert agent.config.address_fields.threshold == 0.88

    def test_flip_only_names(self, tmp_path):
        path = _write_config(
            tmp_path,
            {"field_rules": {"fuzzy_match": {"name_fields": {"algorithm": "levenshtein"}}}},
        )
        agent = ComparisonAgent(load_comparison_config(path))
        assert isinstance(agent.fuzzy_comparator.name_strategy, LevenshteinNameStrategy)
        assert isinstance(agent.fuzzy_comparator.address_strategy, JaccardAddressStrategy)

    def test_unknown_algorithm_rejected_at_construction(self, tmp_path):
        path = _write_config(
            tmp_path,
            {"field_rules": {"fuzzy_match": {"name_fields": {"algorithm": "soundex"}}}},
        )
        with pytest.raises(ValueError):
            ComparisonAgent(load_comparison_config(path))

    def test_thresholds_come_from_config(self, tmp_path):
        path = _write_config(
            tmp_path,
            {
                "field_rules": {
                    "fuzzy_match": {
                        "name_fields": {"threshold": 0.99},
                        "address_fields": {"threshold": 0.99},
                    }
                }
            },
        )
        agent = ComparisonAgent(load_comparison_config(path))
        exact = agent._compare_field("borrower_name", "John Smith", "john smith")
        near = agent._compare_field("borrower_name", "John A Smith", "John Smith")
        assert exact.is_match is True
        assert near.is_match is False
        assert near.similarity_score == pytest.approx(2 / 3)

    def test_field_sets_come_from_config(self, tmp_path):
        path = _write_config(
            tmp_path,
            {"field_rules": {"fuzzy_match": {"name_fields": {"fields": ["custom_name"]}}}},
        )
        agent = ComparisonAgent(load_comparison_config(path))
        result = agent._compare_field("custom_name", "Smith John", "John Smith")
        assert result.is_match is True
        assert result.similarity_score == 1.0
