from pathlib import Path

import pytest

from examsolver.storage.uploads import InvalidImageUpload, store_image_upload


def test_store_image_upload_uses_generated_safe_filename(tmp_path: Path) -> None:
    stored = store_image_upload(
        content=b"png-content",
        content_type="image/png",
        upload_dir=tmp_path,
    )

    assert stored.parent == tmp_path.resolve()
    assert stored.suffix == ".png"
    assert stored.read_bytes() == b"png-content"


@pytest.mark.parametrize(
    ("content", "content_type", "message"),
    [
        (b"", "image/png", "图片文件为空"),
        (b"text", "text/plain", "仅支持"),
    ],
)
def test_store_image_upload_rejects_invalid_files(
    tmp_path: Path,
    content: bytes,
    content_type: str,
    message: str,
) -> None:
    with pytest.raises(InvalidImageUpload, match=message):
        store_image_upload(
            content=content,
            content_type=content_type,
            upload_dir=tmp_path,
        )
