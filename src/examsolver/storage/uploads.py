"""Controlled storage for browser-uploaded solve images."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

ALLOWED_IMAGE_TYPES = {
    "image/bmp": ".bmp",
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_IMAGE_BYTES = 10 * 1024 * 1024


class InvalidImageUpload(ValueError):
    """Raised when an uploaded solve image is unsupported or unsafe."""


def store_image_upload(
    *,
    content: bytes,
    content_type: str | None,
    upload_dir: Path | None = None,
) -> Path:
    """Persist one validated image and return its absolute backend path."""

    suffix = ALLOWED_IMAGE_TYPES.get(content_type or "")
    if suffix is None:
        raise InvalidImageUpload("仅支持 PNG、JPEG、WebP、GIF 或 BMP 图片")
    if not content:
        raise InvalidImageUpload("图片文件为空")
    if len(content) > MAX_IMAGE_BYTES:
        raise InvalidImageUpload("图片不能超过 10 MB")

    target_dir = upload_dir or Path(
        os.getenv("EXAMSOLVER_UPLOAD_DIR", "data/uploads")
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    target = (target_dir / f"{uuid4().hex}{suffix}").resolve()
    target.write_bytes(content)
    return target
