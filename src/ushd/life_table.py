"""Lightweight life table utilities used by the decomposition toolkit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence


@dataclass
class LifeTable:
    """Representation of an abridged life table."""

    age_lower: List[float]
    age_upper: List[Optional[float]]
    n: List[Optional[float]]
    mx: List[float]
    ax: List[float]
    qx: List[float]
    px: List[float]
    lx: List[float]
    dx: List[float]
    Lx: List[float]
    Tx: List[float]
    ex: List[float]

    def column(self, name: str) -> List[float]:
        return getattr(self, name)

    def to_dicts(self) -> List[dict]:
        return [
            {
                "age_lower": self.age_lower[i],
                "age_upper": self.age_upper[i],
                "n": self.n[i],
                "mx": self.mx[i],
                "ax": self.ax[i],
                "qx": self.qx[i],
                "px": self.px[i],
                "lx": self.lx[i],
                "dx": self.dx[i],
                "Lx": self.Lx[i],
                "Tx": self.Tx[i],
                "ex": self.ex[i],
            }
            for i in range(len(self.mx))
        ]

    def to_pandas(self):  # pragma: no cover - optional dependency
        try:
            import pandas as pd
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("pandas is required to convert to a DataFrame") from exc
        return pd.DataFrame(self.to_dicts())


@dataclass
class LifeTableInput:
    age_lower: Iterable[float]
    age_upper: Iterable[Optional[float]]
    mx: Iterable[float]
    ax: Optional[Iterable[float]] = None
    radix: float = 100_000.0


def _validate_inputs(data: LifeTableInput) -> None:
    age_lower = list(data.age_lower)
    age_upper = list(data.age_upper)
    mx = list(data.mx)

    if not (len(age_lower) == len(age_upper) == len(mx)):
        raise ValueError("age_lower, age_upper, and mx must have the same length")
    if len(age_lower) < 2:
        raise ValueError("Life tables require at least two age groups")

    for i, (low, high) in enumerate(zip(age_lower, age_upper)):
        if high is not None and high <= low:
            raise ValueError(f"age_upper must exceed age_lower at row {i}")

    if data.ax is not None:
        ax_list = list(data.ax)
        if len(ax_list) != len(age_lower):
            raise ValueError("ax must have the same length as the age vectors")

    if any(high is None for high in age_upper[:-1]):
        raise ValueError("Only the final age group may be open-ended")


def _compute_ax(
    age_lower: Sequence[float],
    age_upper: Sequence[Optional[float]],
    mx: Sequence[float],
) -> List[float]:
    ax: List[float] = []
    for low, high, rate in zip(age_lower, age_upper, mx):
        if high is None:
            ax.append(1.0 / max(rate, 1e-12))
        else:
            ax.append((high - low) / 2.0)
    return ax


def build_life_table(data: LifeTableInput) -> LifeTable:
    age_lower_list = list(data.age_lower)
    age_upper_list = list(data.age_upper)
    mx_list = list(data.mx)
    ax_list = list(data.ax) if data.ax is not None else None

    _validate_inputs(
        LifeTableInput(
            age_lower=age_lower_list,
            age_upper=age_upper_list,
            mx=mx_list,
            ax=ax_list,
            radix=data.radix,
        )
    )

    age_lower = list(map(float, age_lower_list))
    age_upper = [None if val is None else float(val) for val in age_upper_list]
    mx = [float(val) for val in mx_list]
    if any(rate < 0 for rate in mx):
        raise ValueError("Mortality rates must be non-negative")

    ax = (
        [float(val) for val in ax_list]
        if ax_list is not None
        else _compute_ax(age_lower, age_upper, mx)
    )

    n: List[Optional[float]] = []
    for low, high in zip(age_lower, age_upper):
        if high is None:
            n.append(None)
        else:
            n.append(high - low)

    qx: List[float] = []
    for width, rate, a in zip(n, mx, ax):
        if width is None:
            qx.append(1.0)
        else:
            numerator = width * rate
            denominator = 1.0 + (width - a) * rate
            value = numerator / denominator if denominator else 1.0
            qx.append(max(0.0, min(1.0, value)))

    px = [1.0 - value for value in qx]

    lx: List[float] = [data.radix]
    for prob in px[:-1]:
        lx.append(lx[-1] * prob)

    dx = [l * q for l, q in zip(lx, qx)]

    Lx: List[float] = []
    for width, l_val, d_val, a, rate in zip(n, lx, dx, ax, mx):
        if width is None:
            Lx.append(l_val / max(rate, 1e-12))
        else:
            Lx.append(width * (l_val - d_val) + a * d_val)

    Tx: List[float] = [0.0] * len(Lx)
    Tx[-1] = Lx[-1]
    for i in range(len(Lx) - 2, -1, -1):
        Tx[i] = Tx[i + 1] + Lx[i]

    ex = [t / l if l else 0.0 for t, l in zip(Tx, lx)]

    return LifeTable(
        age_lower=age_lower,
        age_upper=age_upper,
        n=n,
        mx=mx,
        ax=ax,
        qx=qx,
        px=px,
        lx=lx,
        dx=dx,
        Lx=Lx,
        Tx=Tx,
        ex=ex,
    )
