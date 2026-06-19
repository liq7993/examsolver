"""Render a one-question note as a print-quality PDF.

Uses reportlab with the built-in ``STSong-Light`` CID font so Chinese text
renders without bundling a multi-megabyte TTF. Math is shown as its LaTeX
source (same level as the Markdown export); reportlab does not typeset math.
"""

from __future__ import annotations

import json
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

from examsolver.contracts import NoteEntry

_CJK_FONT = "STSong-Light"
_ACCENT = colors.HexColor("#d94e00")
_INK = colors.HexColor("#1d1d1f")
_MUTED = colors.HexColor("#6e6e73")
_registered = False


def export_note_to_pdf(note: NoteEntry) -> bytes:
    """Render one NoteEntry into an in-memory PDF file."""

    _ensure_font()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title=note.title or "单题笔记",
    )
    styles = _build_styles()
    flow = [
        Paragraph(_esc(note.title or "单题笔记"), styles["title"]),
        Paragraph(
            _esc(f"学科：{note.subject or 'unknown'}    题型：{note.question_type}"),
            styles["meta"],
        ),
        Spacer(1, 6),
        Paragraph("题目", styles["h1"]),
        Paragraph(_esc(note.question_latex), styles["body"]),
    ]

    explanation = note.student_explanation
    if explanation is not None:
        flow.append(Paragraph("思路", styles["h1"]))
        flow.append(Paragraph(_esc(explanation.intuition or explanation.summary), styles["body"]))

    flow.append(Paragraph("步骤", styles["h1"]))
    if note.steps:
        items = []
        for step in note.steps:
            text = _esc(step.description)
            if step.formula_latex:
                text += f'<br/><font color="#444444">{_esc(step.formula_latex)}</font>'
            items.append(ListItem(Paragraph(text, styles["body"]), value=step.index))
        flow.append(ListFlowable(items, bulletType="1", leftIndent=16))
    else:
        flow.append(Paragraph("暂无步骤。", styles["body"]))

    flow.append(Paragraph("答案", styles["h1"]))
    flow.append(Paragraph(_esc(_answer_text(note.answer)), styles["answer"]))

    mistakes = list(note.common_mistakes)
    if explanation is not None and explanation.common_mistake:
        if explanation.common_mistake not in mistakes:
            mistakes.append(explanation.common_mistake)
    flow.append(Paragraph("易错点", styles["h1"]))
    if mistakes:
        flow.append(
            ListFlowable(
                [ListItem(Paragraph(_esc(item), styles["body"])) for item in mistakes],
                bulletType="bullet",
                leftIndent=16,
            )
        )
    else:
        flow.append(Paragraph("暂无易错点。", styles["body"]))

    if note.related_formulas:
        flow.append(Paragraph("公式速查", styles["h1"]))
        for formula in note.related_formulas:
            flow.append(Paragraph(_esc(formula.title), styles["h2"]))
            flow.append(Paragraph(_esc(formula.formula_latex), styles["body"]))
            if formula.explanation:
                flow.append(Paragraph(_esc(formula.explanation), styles["muted"]))

    document.build(flow)
    return buffer.getvalue()


def _ensure_font() -> None:
    global _registered
    if _registered:
        return
    pdfmetrics.registerFont(UnicodeCIDFont(_CJK_FONT))
    _registered = True


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()["Normal"]

    def make(name: str, **kwargs: object) -> ParagraphStyle:
        return ParagraphStyle(name, parent=base, fontName=_CJK_FONT, **kwargs)

    return {
        "title": make("ESTitle", fontSize=18, leading=24, alignment=TA_CENTER, spaceAfter=4),
        "meta": make("ESMeta", fontSize=9.5, leading=14, alignment=TA_CENTER, textColor=_MUTED),
        "h1": make("ESH1", fontSize=13, leading=18, spaceBefore=12, spaceAfter=5, textColor=_ACCENT),
        "h2": make("ESH2", fontSize=11, leading=15, spaceBefore=6, spaceAfter=2, textColor=_INK),
        "body": make("ESBody", fontSize=10.5, leading=15.5, textColor=_INK),
        "answer": make("ESAnswer", fontSize=11.5, leading=17, textColor=_INK),
        "muted": make("ESMuted", fontSize=9.5, leading=14, textColor=_MUTED),
    }


def _answer_text(answer: str | dict[str, object] | None) -> str:
    if answer is None:
        return "暂无答案"
    if isinstance(answer, str):
        return answer
    return json.dumps(answer, ensure_ascii=False, indent=2)


def _esc(value: str) -> str:
    return escape(str(value)).replace("\n", "<br/>")
