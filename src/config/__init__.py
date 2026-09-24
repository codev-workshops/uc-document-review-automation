"""Configuration loading."""

from src.config.loader import (
    DEFAULT_CONFIG_PATH,
    ComparisonConfig,
    FuzzyFieldConfig,
    load_comparison_config,
)

__all__ = [
    "DEFAULT_CONFIG_PATH",
    "ComparisonConfig",
    "FuzzyFieldConfig",
    "load_comparison_config",
]
