"""Deterministic function plotting derived from solved results.

This service mirrors :mod:`examsolver.services.explanation`: it takes a
:class:`~examsolver.contracts.SolveResult` and returns an enriched copy via
:func:`dataclasses.replace`, never mutating the input and never failing the
solve pipeline. Plots are produced purely from sympy by re-parsing the
canonical expression strings the calculus skill already recorded in ``meta``
(so there is no fragile re-parsing of raw user input and no LLM involvement).

When the result is not a single-real-variable function, plotting degrades
honestly by returning ``None`` — no fabricated curve is ever drawn.
"""

from __future__ import annotations

import logging
import math
from dataclasses import replace
from typing import Any

import sympy as sp

from examsolver.contracts import PlotData, PlotSeries, SolveResult

logger = logging.getLogger(__name__)

# Sampling window: symmetric x-range and resolution. Kept modest so the JSON
# payload stays small and the client-side SVG renders quickly.
_SAMPLES = 240
_RANGE = 6.0
# Clip wildly large values (e.g. near asymptotes) so the curve stays readable.
_MAX_ABS_Y = 1e6


def attach_plot(result: SolveResult) -> SolveResult:
    """Return a copy of ``result`` with a deterministic plot when possible.

    Returns the original result unchanged when the solved facts do not describe
    a plottable single-variable function (honest degradation).
    """

    data = build_plot(result)
    if data is None:
        return result
    return replace(result, plot=data)


def build_plot(result: SolveResult) -> PlotData | None:
    """Build plot data from the calculus derivative facts, or ``None``."""

    meta = result.meta
    expr_str = meta.get("calculus.derivative.expression")
    deriv_str = meta.get("calculus.derivative.derivative")
    var_str = meta.get("calculus.derivative.variable")
    if not (
        isinstance(expr_str, str)
        and isinstance(deriv_str, str)
        and isinstance(var_str, str)
    ):
        return None

    try:
        var = sp.Symbol(var_str)
        expr = sp.sympify(expr_str)
        deriv = sp.sympify(deriv_str)
    except (sp.SympifyError, TypeError, ValueError) as exc:
        logger.debug("plot skipped: cannot sympify recorded facts: %s", exc)
        return None

    # Only plot genuine single-variable real functions of ``var``.
    if (expr.free_symbols - {var}) or (deriv.free_symbols - {var}):
        return None

    f_series = _sample(expr, var, f"f({var_str})")
    if f_series is None:
        return None
    d_series = _sample(deriv, var, f"f'({var_str})")

    series = [f_series] + ([d_series] if d_series is not None else [])
    return PlotData(
        title="函数与其导数",
        x_label=var_str,
        y_label="y",
        series=tuple(series),
    )


def _sample(expr: Any, var: Any, label: str) -> PlotSeries | None:
    """Sample ``expr`` over the x-window, skipping un-evaluable points."""

    try:
        fn = sp.lambdify(var, expr, "math")
    except Exception as exc:  # noqa: BLE001 - lambdify failure -> no curve
        logger.debug("plot skipped: lambdify failed for %s: %s", label, exc)
        return None

    points: list[tuple[float, float]] = []
    step = (2 * _RANGE) / (_SAMPLES - 1)
    for i in range(_SAMPLES):
        x = -_RANGE + i * step
        try:
            y = fn(x)
        except Exception:  # noqa: BLE001 - per-point domain errors are skipped
            continue
        if not isinstance(y, (int, float)) or isinstance(y, bool):
            continue
        if not math.isfinite(y) or abs(y) > _MAX_ABS_Y:
            continue
        points.append((float(x), float(y)))

    if len(points) < 2:
        return None
    return PlotSeries(label=label, points=tuple(points))
