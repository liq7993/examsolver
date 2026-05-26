# Troubleshooting

## Windows + PaddlePaddle

`paddleocr` depends on `paddlepaddle`, and Windows installs can be sensitive to Python,
CPU/GPU, and wheel availability.

Known baseline for this project:

- Python: `>=3.11`
- Requested dependency: `paddlepaddle>=3`
- OCR dependency group: `paddleocr>=3`

If `uv sync` fails on Windows:

1. Confirm the active Python version is 3.11 or newer.
2. Prefer the CPU wheel first; GPU wheels depend on the local CUDA stack.
3. If no compatible `paddlepaddle>=3` wheel exists for the machine, pin the newest
   compatible PaddlePaddle wheel and record the pin here.
4. If PaddlePaddle remains blocked, use `rapidocr-onnxruntime` as the documented fallback
   from `ROADMAP.md`, but keep the OCR adapter boundary unchanged.

Do not bypass the OCR adapter by adding Paddle-specific calls outside `src/examsolver/multimodal/`.

`PaddleOCR` is lazy-loaded by `src/examsolver/multimodal/ocr_paddle.py`. Importing the
module should not initialize or download models; the first real `recognize(...)` call owns
that cost. The slow timing test is opt-in:

```bash
EXAMSOLVER_RUN_SLOW_OCR=1 uv run pytest tests/multimodal/ -m slow -q
```

## uv sync on `/mnt/d`

Observed during M0-02 on WSL with the project under `/mnt/d/examsolver/examsolver`:

```text
warning: Failed to hardlink files; falling back to full copy.
```

This is expected when the uv cache and `.venv` target live on different filesystems. It is
not an install failure, but it makes sync slower because uv copies large ML wheels instead
of hardlinking them.

Use one of these when the warning is noisy:

```bash
UV_LINK_MODE=copy uv sync
uv sync --link-mode=copy
```

Also note that making OCR/RAG dependencies core dependencies pulls a large ML stack
(`torch`, CUDA wheels, `paddlepaddle`, `paddleocr`, `sentence-transformers`). A clean sync
can take several minutes and multiple GB of disk space.
