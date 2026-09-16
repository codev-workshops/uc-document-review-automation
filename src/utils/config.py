"""Comparison configuration loading."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from src.comparators.field_comparator import CRITICAL_FIELDS, EXACT_MATCH_FIELDS
from src.comparators.field_sets import (
    ADDRESS_FIELDS,
    AMOUNT_FIELDS,
    DATE_FIELDS,
    NAME_FIELDS,
    RATE_FIELDS,
)

CONFIG_PATH_ENV = "COMPARISON_RULES_PATH"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config/comparison_rules.yaml"


class ConfigError(ValueError):
    """Raised when comparison configuration is incomplete or invalid."""


@dataclass(frozen=True)
class FuzzyGroupConfig:
    threshold: float
    fields: frozenset[str]


@dataclass(frozen=True)
class NumericGroupConfig:
    tolerance: float
    fields: frozenset[str]
    relative_tolerance: float = 0.0


@dataclass(frozen=True)
class FuzzyMatchConfig:
    name_fields: FuzzyGroupConfig
    address_fields: FuzzyGroupConfig
    algorithm: str = "jaccard"
    name_noise: Optional[frozenset[str]] = None
    address_abbreviations: Optional[dict[str, str]] = field(default=None)


@dataclass(frozen=True)
class ComparisonConfig:
    confidence_threshold: float
    exact_match_fields: frozenset[str]
    fuzzy_match: FuzzyMatchConfig
    amount_fields: NumericGroupConfig
    rate_fields: NumericGroupConfig
    date_fields: frozenset[str]
    critical_fields: frozenset[str]
    low_confidence_threshold: float = 0.90

    @classmethod
    def default(cls) -> "ComparisonConfig":
        from src.comparators.fuzzy_comparator import ADDRESS_ABBREVIATIONS, NAME_NOISE

        return cls(
            confidence_threshold=0.95,
            exact_match_fields=frozenset(EXACT_MATCH_FIELDS),
            fuzzy_match=FuzzyMatchConfig(
                name_fields=FuzzyGroupConfig(0.85, frozenset(NAME_FIELDS)),
                address_fields=FuzzyGroupConfig(0.80, frozenset(ADDRESS_FIELDS)),
                algorithm="jaccard",
                name_noise=frozenset(NAME_NOISE),
                address_abbreviations=dict(ADDRESS_ABBREVIATIONS),
            ),
            amount_fields=NumericGroupConfig(0.01, frozenset(AMOUNT_FIELDS)),
            rate_fields=NumericGroupConfig(0.001, frozenset(RATE_FIELDS)),
            date_fields=frozenset(DATE_FIELDS),
            critical_fields=frozenset(CRITICAL_FIELDS),
            low_confidence_threshold=0.90,
        )


def _required(data: dict, path: str):
    current = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ConfigError(path)
        current = current[part]
    return current


def load_comparison_config(path: Optional[str | Path] = None) -> ComparisonConfig:
    selected = Path(path) if path is not None else Path(
        os.environ.get(CONFIG_PATH_ENV, DEFAULT_CONFIG_PATH)
    )
    with selected.open() as stream:
        data = yaml.safe_load(stream) or {}

    fuzzy = _required(data, "field_rules.fuzzy_match")
    amount = _required(data, "field_rules.amount_fields")
    field_rules = _required(data, "field_rules")
    date_group = field_rules.get("date_fields", {})
    return ComparisonConfig(
        confidence_threshold=float(_required(data, "confidence_threshold")),
        exact_match_fields=frozenset(_required(data, "field_rules.exact_match")),
        fuzzy_match=FuzzyMatchConfig(
            name_fields=FuzzyGroupConfig(
                float(_required(data, "field_rules.fuzzy_match.name_fields.threshold")),
                frozenset(_required(data, "field_rules.fuzzy_match.name_fields.fields")),
            ),
            address_fields=FuzzyGroupConfig(
                float(_required(data, "field_rules.fuzzy_match.address_fields.threshold")),
                frozenset(_required(data, "field_rules.fuzzy_match.address_fields.fields")),
            ),
            algorithm=fuzzy.get("algorithm", "jaccard"),
            name_noise=(
                frozenset(fuzzy["name_noise"])
                if fuzzy.get("name_noise") is not None
                else None
            ),
            address_abbreviations=(
                dict(fuzzy["address_abbreviations"])
                if fuzzy.get("address_abbreviations") is not None
                else None
            ),
        ),
        amount_fields=NumericGroupConfig(
            float(_required(data, "field_rules.amount_fields.tolerance")),
            frozenset(_required(data, "field_rules.amount_fields.fields")),
            float(amount.get("relative_tolerance", 0.0)),
        ),
        rate_fields=NumericGroupConfig(
            float(_required(data, "field_rules.rate_fields.tolerance")),
            frozenset(_required(data, "field_rules.rate_fields.fields")),
        ),
        date_fields=frozenset(date_group.get("fields", DATE_FIELDS)),
        critical_fields=frozenset(_required(data, "critical_fields")),
        low_confidence_threshold=float(data.get("low_confidence_threshold", 0.90)),
    )
