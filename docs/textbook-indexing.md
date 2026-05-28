# Textbook Indexing

Place local textbook PDFs under `data/textbooks/`. This directory is gitignored so large or copyrighted PDFs are not committed.

For M3-07 acceptance, put a 10-30 page mechanical or tolerance textbook sample at one of these paths:

- `data/textbooks/tolerance.pdf`
- `data/textbooks/_sample.pdf`

Then run:

```bash
uv run python scripts/index_textbook.py data/textbooks/tolerance.pdf --subject tolerance --title "公差与测量"
```

If the same PDF path has already been indexed, rerun with `--force` to replace only that document's chunks and vectors.
