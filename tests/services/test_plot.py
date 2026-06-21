from examsolver.contracts import SolveResult
from examsolver.services.plot import attach_plot, build_plot


def _derivative_result(expression: str, derivative: str, variable: str = "x") -> SolveResult:
    """Build a SolveResult carrying the meta the calculus skill records."""

    return SolveResult(
        question_type="derivative",
        skill="calculus.derivative",
        steps=[],
        answer="$2 x$",
        meta={
            "success": True,
            "calculus.derivative.expression": expression,
            "calculus.derivative.derivative": derivative,
            "calculus.derivative.variable": variable,
        },
    )


def test_build_plot_samples_function_and_derivative() -> None:
    plot = build_plot(_derivative_result("x**2", "2*x"))

    assert plot is not None
    assert plot.title == "函数与其导数"
    assert plot.x_label == "x"
    assert [series.label for series in plot.series] == ["f(x)", "f'(x)"]
    # f(x)=x^2 is even -> endpoints match at 36; f'(x)=2x -> -12 and 12.
    assert plot.series[0].points[0] == (-6.0, 36.0)
    assert plot.series[0].points[-1] == (6.0, 36.0)
    assert plot.series[1].points[0] == (-6.0, -12.0)
    assert plot.series[1].points[-1] == (6.0, 12.0)


def test_attach_plot_sets_plot_without_changing_facts() -> None:
    result = _derivative_result("x**2", "2*x")

    enriched = attach_plot(result)

    assert enriched is not result
    assert enriched.plot is not None
    assert enriched.answer == result.answer
    assert enriched.skill == result.skill
    assert enriched.meta == result.meta


def test_build_plot_returns_none_without_calculus_meta() -> None:
    result = SolveResult(
        question_type="matrix_mul",
        skill="linear_algebra.matrix_mul",
        steps=[],
        answer={"result": [[1]]},
        meta={"success": True},
    )

    assert build_plot(result) is None


def test_attach_plot_is_noop_when_not_plottable() -> None:
    result = SolveResult(
        question_type="unknown",
        skill="unknown",
        steps=[],
        answer=None,
        meta={},
    )

    assert attach_plot(result) is result


def test_build_plot_rejects_multivariable_expression() -> None:
    assert build_plot(_derivative_result("x*y", "y")) is None


def test_build_plot_skips_domain_errors_without_faking_points() -> None:
    # log(x) is undefined for x <= 0; those samples are skipped, never invented.
    plot = build_plot(_derivative_result("log(x)", "1/x"))

    assert plot is not None
    f_series = plot.series[0]
    assert f_series.label == "f(x)"
    assert 0 < len(f_series.points) < 240
    assert all(x > 0 for x, _ in f_series.points)


def test_build_plot_clips_unbounded_samples() -> None:
    plot = build_plot(_derivative_result("1/x", "-1/x**2"))

    assert plot is not None
    for series in plot.series:
        for _, y in series.points:
            assert abs(y) <= 1e6
