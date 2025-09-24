"""Utilities for working with US Health Disparities life tables."""

from .life_table import LifeTable, LifeTableInput, build_life_table
from .decomposition import (
    DecompositionResult,
    decompose_between_counties,
    horiuchi_decomposition,
)

__all__ = [
    "LifeTable",
    "LifeTableInput",
    "build_life_table",
    "DecompositionResult",
    "horiuchi_decomposition",
    "decompose_between_counties",
]
