# M3 Acceptance

Date: 2026-05-29

## Quality Gates

- `uv run ruff check .`: passed
- `uv run mypy src tests`: passed, `Success: no issues found in 103 source files`
- `uv run pytest -q`: passed, `177 passed, 3 skipped in 21.07s`
- Focused RAG tests after M3-10 changes: `10 passed in 4.04s`

## Textbook Index

Command:

```bash
uv run python scripts/index_textbook.py data/textbooks/tolerance.pdf --subject tolerance --title "公差与测量"
```

Result:

```text
/mnt/d/examsolver/examsolver/data/textbooks/tolerance.pdf is already indexed as 268d9557-5863-54e8-b746-a4dab00f1b7a; reuse pages=20 chunks=240. Rerun with --force to overwrite.
Indexed pages=20 chunks=240 elapsed=0.09s errors=0
```

Acceptance: passed, `240 >= 50` chunks.

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
  "citations_count": 5,
  "note_citations_count": 5
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
  "citations_count": 5,
  "note_citations_count": 5
}
```

Acceptance: passed, both smoke responses include textbook citations.

## OCR Timing

Image: `tests/fixtures/ocr/handwritten_formula.png`

Measured command ran two OCR calls in one process so model initialization and per-image processing could be separated.

```text
cold=117.008s warm=0.952s chars=11 bboxes=2 confidence=0.706 text='√-×23\n++=2×'
```

Acceptance: passed for processing time, `0.952s < 3s`. Cold start remains dominated by PaddleOCR model initialization.

## RAG Coverage

- Happy path: `tests/rag/test_retriever.py::test_retrieve_returns_hits_under_cosine_distance_threshold`
- Empty result: `tests/rag/test_retriever.py::test_retrieve_returns_empty_when_all_distances_miss`
- Store/index idempotency and chunk count coverage added in M3-10:
  - `tests/rag/test_index_textbook.py::test_duplicate_source_path_reuses_existing_index`
  - `tests/rag/test_store.py::test_get_and_delete_document_by_source_path`

## Followup

- Reduce embedding cold-start latency. Each `scripts/smoke.py` run starts a new process and reloads `sentence-transformers`, including Hugging Face cache metadata checks.
- Document or automate PaddleOCR model warmup. Runtime image processing is under 3s, but cold initialization was 117s in this environment.
