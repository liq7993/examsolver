from examsolver.contracts import SolveRequest
from examsolver.pipeline.classifier import classify
from examsolver.pipeline.dispatcher import dispatch_or_unknown
from examsolver.pipeline.formatter import format_response
from examsolver.pipeline.normalizer import normalize
from examsolver.services.export.markdown_exporter import export_to_markdown


def test_export_to_markdown_includes_complete_solve_artifact() -> None:
    question = normalize(SolveRequest(question="求 x^2 对 x 的导数"))
    response = format_response(question, dispatch_or_unknown(question, classify(question)))

    markdown = export_to_markdown(question=question.raw_text, response=response)

    assert markdown.startswith("# Examsolver 解题笔记")
    assert "## 题目" in markdown
    assert "求 x^2 对 x 的导数" in markdown
    assert "## 最终答案" in markdown
    assert "$\\frac{d}{dx}(x^2) = 2x$" in markdown
    assert "## 步骤" in markdown
    assert "## 学生解释" in markdown
