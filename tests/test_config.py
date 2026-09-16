from pathlib import Path

import pytest

from src.agents.comparison_agent import ComparisonAgent
from src.comparators.field_comparator import CRITICAL_FIELDS, EXACT_MATCH_FIELDS
from src.comparators.field_sets import ADDRESS_FIELDS, AMOUNT_FIELDS, NAME_FIELDS, RATE_FIELDS
from src.comparators.fuzzy_comparator import FuzzyComparator, UnknownAlgorithmError
from src.utils.config import (
    ComparisonConfig,
    ConfigError,
    load_comparison_config,
)


class TestComparisonConfig:
    def test_checked_in_config_matches_field_sets(self):
        config = load_comparison_config()
        assert config.critical_fields == frozenset(CRITICAL_FIELDS)
        assert config.exact_match_fields == frozenset(EXACT_MATCH_FIELDS)
        assert config.fuzzy_match.name_fields.fields == frozenset(NAME_FIELDS)
        assert config.fuzzy_match.address_fields.fields == frozenset(ADDRESS_FIELDS)
        assert config.amount_fields.fields == frozenset(AMOUNT_FIELDS)
        assert config.rate_fields.fields == frozenset(RATE_FIELDS)
        assert config.fuzzy_match.algorithm == "jaccard"
        assert config.fuzzy_match.name_fields.threshold == 0.85
        assert config.fuzzy_match.address_fields.threshold == 0.80
        assert config.confidence_threshold == 0.95

    def test_default_matches_checked_in_config(self):
        loaded = load_comparison_config()
        default = ComparisonConfig.default()
        assert loaded.confidence_threshold == default.confidence_threshold
        assert loaded.exact_match_fields == default.exact_match_fields
        assert loaded.fuzzy_match == default.fuzzy_match
        assert loaded.amount_fields == default.amount_fields
        assert loaded.rate_fields == default.rate_fields
        assert loaded.date_fields == default.date_fields
        assert loaded.critical_fields == default.critical_fields

    def test_custom_threshold_changes_name_matching(self, tmp_path: Path):
        source = Path("config/comparison_rules.yaml").read_text()
        custom = tmp_path / "rules.yaml"
        custom.write_text(source.replace("threshold: 0.85", "threshold: 0.50", 1))
        assert ComparisonAgent(config=custom)._compare_field(
            "borrower_name", "John Smith", "John A Smith"
        ).is_match
        assert not ComparisonAgent()._compare_field(
            "borrower_name", "John Smith", "John A Smith"
        ).is_match

    def test_env_override(self, monkeypatch, tmp_path: Path):
        source = Path("config/comparison_rules.yaml").read_text()
        custom = tmp_path / "rules.yaml"
        custom.write_text(source.replace("confidence_threshold: 0.95", "confidence_threshold: 0.75", 1))
        monkeypatch.setenv("COMPARISON_RULES_PATH", str(custom))
        assert load_comparison_config().confidence_threshold == 0.75

    def test_missing_required_key(self, tmp_path: Path):
        path = tmp_path / "rules.yaml"
        path.write_text("confidence_threshold: 0.95\n")
        with pytest.raises(ConfigError, match="field_rules"):
            load_comparison_config(path)

    def test_unknown_algorithm(self, tmp_path: Path):
        source = Path("config/comparison_rules.yaml").read_text()
        custom = tmp_path / "rules.yaml"
        custom.write_text(source.replace("algorithm: jaccard", "algorithm: soundex", 1))
        with pytest.raises(UnknownAlgorithmError):
            ComparisonAgent(config=custom)
        with pytest.raises(UnknownAlgorithmError):
            FuzzyComparator(algorithm="soundex")
