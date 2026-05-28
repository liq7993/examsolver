# M3 Acceptance

Date: 2026-05-28

## Quality Gates

- `uv run ruff check .`: passed
- `uv run mypy src tests`: passed, 99 source files checked
- `uv run pytest -q`: passed, 169 passed / 3 skipped
- `uv run pytest tests/rag/ -q`: passed, 23 passed

`tests/rag/` includes retriever happy-path, empty/no-hit result, and cross-subject isolation coverage.

## Textbook Indexing

Command:

```bash
uv run python scripts/index_textbook.py data/textbooks/tolerance.pdf --subject tolerance --title "公差与测量"
```

Result:

- Source: `data/textbooks/tolerance.pdf`
- Text path: embedded PDF text, no OCR fallback needed
- Pages: 20
- Chunks: 240
- Errors: 0
- Elapsed: 93.22s

This satisfies the M3 exit requirement of at least 50 chunks.

## Smoke Outputs

Command:

```bash
uv run python scripts/smoke.py "H7/g6 是什么配合？"
```

Excerpt:

```json
{
  "success": true,
  "subject": "tolerance",
  "question_type": "fit_type",
  "skill": "tolerance.fit_type",
  "answer": "H7/g6 属于间隙配合",
  "citations_count": 3,
  "first_citation": {
    "source": "公差与测量",
    "page": 1,
    "snippet": "# H7配合"
  }
}
```

Command:

```bash
uv run python scripts/smoke.py "请说明孔的基本偏差代号 H 和轴的 h 区别"
```

Excerpt:

```json
{
  "success": true,
  "subject": "tolerance",
  "question_type": "fit_type",
  "skill": "tolerance.fit_type",
  "answer": "H/h 属于间隙配合",
  "citations_count": 3
}
```

## OCR Timing

Fixture: `tests/fixtures/ocr/handwritten_formula.png`

Measurement method: initialize PaddleOCR once, run one warmup recognition, then measure the second recognition call.

Result:

- Elapsed: 0.417s
- Blocks: 2
- Confidence: 0.706
- Recognized excerpt: `√-×23 | ++=2×`

This satisfies the M3 exit requirement of OCR processing a handwritten formula image in under 3s. The recognition text is imperfect, but the current M3 exit criterion is latency; recognition quality should be improved with a stronger formula/handwriting OCR path later.

## Followup

- SentenceTransformer still performs Hugging Face metadata HEAD requests unless `HF_TOKEN` or a fully local model path is configured.
- Local BACKLOG still lists M3-09 as unchecked and the corresponding Library API files are absent in this tree; this report only closes the M3-10 acceptance card.
