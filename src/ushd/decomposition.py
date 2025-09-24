"""Life expectancy decomposition using stepwise replacement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple

from .life_table import LifeTableInput, build_life_table


@dataclass
class DecompositionResult:
    age_lower: List[float]
    age_upper: List[Optional[float]]
    contribution: List[float]

    def to_records(self) -> List[dict]:
        return [
            {
                "age_lower": self.age_lower[i],
                "age_upper": self.age_upper[i],
                "contribution": self.contribution[i],
            }
            for i in range(len(self.age_lower))
        ]

    def to_pandas(self):  # pragma: no cover - optional dependency
        try:
            import pandas as pd
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("pandas is required to create a DataFrame") from exc
        return pd.DataFrame(self.to_records())


def _life_expectancy_from_mx(
    mx: Sequence[float],
    age_lower: Sequence[float],
    age_upper: Sequence[Optional[float]],
    ax: Optional[Sequence[float]],
) -> float:
    table = build_life_table(
        LifeTableInput(age_lower=age_lower, age_upper=age_upper, mx=mx, ax=ax)
    )
    return table.ex[0]


def _numeric_gradient(
    func,
    mx: Sequence[float],
    step: float = 1e-5,
) -> List[float]:
    gradients: List[float] = []
    for idx in range(len(mx)):
        perturbed = list(mx)
        perturbed[idx] += step
        upper = func(perturbed)
        perturbed[idx] -= 2 * step
        lower = func(perturbed)
        gradients.append((upper - lower) / (2 * step))
    return gradients


def horiuchi_decomposition(
    baseline_mx: Iterable[float],
    comparison_mx: Iterable[float],
    age_lower: Iterable[float],
    age_upper: Iterable[Optional[float]],
    ax: Optional[Iterable[float]] = None,
    steps: int = 50,
) -> DecompositionResult:
    baseline = list(map(float, baseline_mx))
    comparison = list(map(float, comparison_mx))
    if len(baseline) != len(comparison):
        raise ValueError("baseline_mx and comparison_mx must have the same length")

    age_lower = list(map(float, age_lower))
    age_upper = [None if val is None else float(val) for val in age_upper]
    ax = None if ax is None else list(map(float, ax))

    def func(values: Sequence[float]) -> float:
        return _life_expectancy_from_mx(values, age_lower, age_upper, ax)

    delta = [b - a for a, b in zip(baseline, comparison)]
    contributions = [0.0 for _ in delta]
    for step_idx in range(steps):
        weight = (step_idx + 0.5) / steps
        mx_step = [a + weight * d for a, d in zip(baseline, delta)]
        gradient = _numeric_gradient(func, mx_step)
        for i, (grad, diff) in enumerate(zip(gradient, delta)):
            contributions[i] += grad * diff / steps

    return DecompositionResult(
        age_lower=age_lower,
        age_upper=age_upper,
        contribution=contributions,
    )


def _ensure_records(data) -> List[Mapping[str, object]]:
    if isinstance(data, list):
        return data  # assume list of dict-like structures
    if hasattr(data, "to_dict"):
        try:
            return data.to_dict("records")  # type: ignore[call-arg]
        except TypeError:
            pass
    raise TypeError("data must be a list of mappings or a pandas DataFrame")


def _key(age_lower: object, age_upper: object) -> Tuple[float, Optional[float]]:
    lower = float(age_lower)
    upper = None if age_upper is None else float(age_upper)
    return lower, upper


def decompose_between_counties(
    data,
    county_col: str,
    race_col: str,
    sex_col: str,
    age_lower_col: str,
    age_upper_col: str,
    mx_col: str,
    county_a: str,
    county_b: str,
    race: str,
    sex: str,
    ax_col: Optional[str] = None,
    steps: int = 50,
) -> List[dict]:
    records = _ensure_records(data)
    cohort = [row for row in records if row.get(race_col) == race and row.get(sex_col) == sex]
    if not cohort:
        raise ValueError("No rows found for the specified race/sex cohort")

    county_a_rows = [row for row in cohort if row.get(county_col) == county_a]
    county_b_rows = [row for row in cohort if row.get(county_col) == county_b]
    if not county_a_rows or not county_b_rows:
        raise ValueError("Both counties must have data for the specified cohort")

    index_a = {
        _key(row[age_lower_col], row[age_upper_col]): row for row in county_a_rows
    }
    index_b = {
        _key(row[age_lower_col], row[age_upper_col]): row for row in county_b_rows
    }

    common_keys = sorted(set(index_a.keys()) & set(index_b.keys()))
    if not common_keys:
        raise ValueError("No overlapping age groups available for decomposition")

    baseline_mx = [float(index_a[key][mx_col]) for key in common_keys]
    comparison_mx = [float(index_b[key][mx_col]) for key in common_keys]
    age_lower = [key[0] for key in common_keys]
    age_upper = [key[1] for key in common_keys]

    ax_values: Optional[List[float]] = None
    if ax_col is not None:
        collected: List[float] = []
        for key in common_keys:
            val_a = index_a[key].get(ax_col)
            val_b = index_b[key].get(ax_col)
            chosen = val_a if val_a is not None else val_b
            if chosen is None:
                collected = []
                break
            collected.append(float(chosen))
        if collected:
            ax_values = collected

    result = horiuchi_decomposition(
        baseline_mx=baseline_mx,
        comparison_mx=comparison_mx,
        age_lower=age_lower,
        age_upper=age_upper,
        ax=ax_values,
        steps=steps,
    )

    total_gap = sum(result.contribution)
    output = result.to_records()
    for row in output:
        row.update(
            {
                "county_a": county_a,
                "county_b": county_b,
                "race": race,
                "sex": sex,
                "life_expectancy_difference": total_gap,
            }
        )
    return output
