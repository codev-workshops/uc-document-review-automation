"""Loads comparison rules from ``config/comparison_rules.yaml``.

Every value has a default matching the historical hardcoded behaviour, so a
missing or partial config file degrades gracefully to the previous pipeline.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "comparison_rules.yaml"
CONFIG_PATH_ENV_VAR = "COMPARISON_RULES_PATH"

DEFAULT_ALGORITHM = "jaccard"

DEFAULT_NAME_FIELDS = frozenset(
    {"borrower_name", "original_borrower", "new_borrower", "recipient_name"}
)
DEFAULT_ADDRESS_FIELDS = frozenset({"property_address", "recipient_address"})
DEFAULT_AMOUNT_FIELDS = frozenset(
    {"loan_amount", "original_amount", "current_balance", "new_payment_amount"}
)
DEFAULT_RATE_FIELDS = frozenset(
    {"interest_rate", "new_interest_rate", "coverage_percentage"}
)
DEFAULT_NAME_THRESHOLD = 0.85
DEFAULT_ADDRESS_THRESHOLD = 0.80
DEFAULT_CONFIDENCE_THRESHOLD = 0.95


@dataclass(frozen=True)
class FuzzyFieldConfig:
    """Algorithm + threshold for one family of fuzzy-matched fields."""

    fields: frozenset[str]
    algorithm: str
    threshold: float
    algorithm_thresholds: dict[str, float] = field(default_factory=dict)

    def threshold_for(self, algorithm: str) -> float:
        """Threshold calibrated for ``algorithm``; falls back to the active one."""
        return self.algorithm_thresholds.get(algorithm, self.threshold)


@dataclass(frozen=True)
class ComparisonConfig:
    """Resolved comparison configuration."""

    name_fields: FuzzyFieldConfig
    address_fields: FuzzyFieldConfig
    amount_fields: frozenset[str]
    rate_fields: frozenset[str]
    amount_tolerance: float
    rate_tolerance: float
    confidence_threshold: float
    source_path: Optional[Path] = None

    @classmethod
    def defaults(cls) -> "ComparisonConfig":
        return cls(
            name_fields=FuzzyFieldConfig(
                DEFAULT_NAME_FIELDS, DEFAULT_ALGORITHM, DEFAULT_NAME_THRESHOLD
            ),
            address_fields=FuzzyFieldConfig(
                DEFAULT_ADDRESS_FIELDS, DEFAULT_ALGORITHM, DEFAULT_ADDRESS_THRESHOLD
            ),
            amount_fields=DEFAULT_AMOUNT_FIELDS,
            rate_fields=DEFAULT_RATE_FIELDS,
            amount_tolerance=0.01,
            rate_tolerance=0.001,
            confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
        )

    def with_algorithms(
        self,
        name_algorithm: Optional[str] = None,
        address_algorithm: Optional[str] = None,
    ) -> "ComparisonConfig":
        """Return a copy with the given algorithms (and their calibrated thresholds)."""
        name_cfg = self.name_fields
        addr_cfg = self.address_fields
        if name_algorithm is not None:
            name_cfg = FuzzyFieldConfig(
                name_cfg.fields,
                name_algorithm,
                name_cfg.threshold_for(name_algorithm),
                name_cfg.algorithm_thresholds,
            )
        if address_algorithm is not None:
            addr_cfg = FuzzyFieldConfig(
                addr_cfg.fields,
                address_algorithm,
                addr_cfg.threshold_for(address_algorithm),
                addr_cfg.algorithm_thresholds,
            )
        return ComparisonConfig(
            name_fields=name_cfg,
            address_fields=addr_cfg,
            amount_fields=self.amount_fields,
            rate_fields=self.rate_fields,
            amount_tolerance=self.amount_tolerance,
            rate_tolerance=self.rate_tolerance,
            confidence_threshold=self.confidence_threshold,
            source_path=self.source_path,
        )


def _parse_fuzzy_section(
    section: Any, default: FuzzyFieldConfig
) -> FuzzyFieldConfig:
    if not isinstance(section, dict):
        return default
    fields = section.get("fields")
    algorithm = str(section.get("algorithm", default.algorithm)).lower()
    raw_thresholds = section.get("algorithm_thresholds") or {}
    algorithm_thresholds = {
        str(k).lower(): float(v) for k, v in raw_thresholds.items()
    }
    if "threshold" in section:
        threshold = float(section["threshold"])
    else:
        threshold = algorithm_thresholds.get(algorithm, default.threshold)
    return FuzzyFieldConfig(
        fields=frozenset(fields) if fields else default.fields,
        algorithm=algorithm,
        threshold=threshold,
        algorithm_thresholds=algorithm_thresholds,
    )


def _parse_field_list(section: Any, default: frozenset[str]) -> frozenset[str]:
    if isinstance(section, dict) and section.get("fields"):
        return frozenset(section["fields"])
    return default


def _parse_tolerance(section: Any, default: float) -> float:
    if isinstance(section, dict) and "tolerance" in section:
        return float(section["tolerance"])
    return default


def parse_comparison_config(
    raw: Any, source_path: Optional[Path] = None
) -> ComparisonConfig:
    """Build a ``ComparisonConfig`` from parsed YAML data."""
    defaults = ComparisonConfig.defaults()
    if not isinstance(raw, dict):
        return defaults

    field_rules = raw.get("field_rules") or {}
    fuzzy = field_rules.get("fuzzy_match") or {}

    return ComparisonConfig(
        name_fields=_parse_fuzzy_section(fuzzy.get("name_fields"), defaults.name_fields),
        address_fields=_parse_fuzzy_section(
            fuzzy.get("address_fields"), defaults.address_fields
        ),
        amount_fields=_parse_field_list(
            field_rules.get("amount_fields"), defaults.amount_fields
        ),
        rate_fields=_parse_field_list(field_rules.get("rate_fields"), defaults.rate_fields),
        amount_tolerance=_parse_tolerance(
            field_rules.get("amount_fields"), defaults.amount_tolerance
        ),
        rate_tolerance=_parse_tolerance(
            field_rules.get("rate_fields"), defaults.rate_tolerance
        ),
        confidence_threshold=float(
            raw.get("confidence_threshold", defaults.confidence_threshold)
        ),
        source_path=source_path,
    )


def load_comparison_config(path: Optional[os.PathLike | str] = None) -> ComparisonConfig:
    """Load the comparison config from ``path`` (default: config/comparison_rules.yaml).

    Resolution order: explicit ``path`` > ``COMPARISON_RULES_PATH`` env var >
    default file. A missing file yields the built-in defaults.
    """
    resolved = Path(path or os.environ.get(CONFIG_PATH_ENV_VAR) or DEFAULT_CONFIG_PATH)
    if not resolved.is_file():
        logger.warning("Comparison config %s not found; using defaults", resolved)
        return ComparisonConfig.defaults()
    with resolved.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return parse_comparison_config(raw, source_path=resolved)
